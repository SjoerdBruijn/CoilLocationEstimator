#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  3 07:59:11 2024

@author: sjoerdbruijn
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure  # Import Figure

class AnimationApp:
    """
    A class representing an animation application.
    Attributes:
        root (tkinter.Tk): The root window of the application.
        head (numpy.ndarray): The head reference data.
        coil (numpy.ndarray): The coil reference data.
        headstimpoint (numpy.ndarray): The head stimulation point data.
        coilstimpoint (numpy.ndarray): The coil stimulation point data.
        dist (numpy.ndarray): The distance between two coil midpoints.
        is_paused (bool): Flag indicating whether the animation is paused.
        current_frame (int): The current frame of the animation.
        num_frames (int): The total number of frames in the animation.
        slider_moving (bool): Flag indicating whether the slider is being moved.
        fig (matplotlib.figure.Figure): The matplotlib figure for the animation.
        ax1 (matplotlib.axes.Axes): The time series subplot.
        ax2 (matplotlib.axes.Axes): The 3D subplot.
        line (matplotlib.lines.Line2D): The line representing the distance between two coil midpoints.
        scat1 (mpl_toolkits.mplot3d.art3d.Path3DCollection): The scatter plot for head markers.
        scat2 (mpl_toolkits.mplot3d.art3d.Path3DCollection): The scatter plot for coil markers.
        scat3 (mpl_toolkits.mplot3d.art3d.Path3DCollection): The scatter plot for head stimulation points.
        scat4 (mpl_toolkits.mplot3d.art3d.Path3DCollection): The scatter plot for coil stimulation points.
        canvas (matplotlib.backends.backend_tkagg.FigureCanvasTkAgg): The canvas for embedding the plot in Tkinter.
        play_button (ttk.Button): The button for playing the animation.
        pause_button (ttk.Button): The button for pausing the animation.
        slider (ttk.Scale): The slider for scrolling through the animation.
    Methods:
        __init__(self, coildatastruct): Initializes the AnimationApp object.
        play(self): Plays the animation.
        pause(self): Pauses the animation.
        slider_update(self, val): Updates the animation plot based on the slider value.
        update_plot(self, frame): Updates the time series plot and 3D scatter plot.
    """

    def __init__(self,coildatastruct, master=None, auto_mainloop=True, live_mode=False, on_close_callback=None):
        self.live_mode = live_mode
        self._owns_mainloop = master is None
        self.on_close_callback = on_close_callback
        self.closed = False
        if master is None:
            self.root =  tk.Tk()
        else:
            self.root = tk.Toplevel(master)
        self.root.title("Animation with Play/Pause and Slider")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        #data 
        self.head=np.array(coildatastruct["headexpdata"], copy=True)
        self.coil=np.array(coildatastruct["coilexpdata"], copy=True)
        self.headstimpoint=np.array(coildatastruct["headstimpoint"], copy=True)
        self.coilstimpoint=np.array(coildatastruct["coilstimpoint"], copy=True)
        self.headmarkernames=list(coildatastruct.get("headmarkernames", []))
        self.coilmarkernames=list(coildatastruct.get("coilmarkernames", []))
        self.dist=self._compute_dist()

        # Initialize variables
        self.is_paused = True
        self.current_frame = 0
        self.num_frames = max(np.shape(self.head)[0], 1)
        self.slider_moving = False  # Flag to prevent recursive slider updates
        self.live_history_limit = 500
        self.slider_update_stride = 5
        self.distance_update_stride = 10
        self.frame_interval_ms = 10
        self.after_job = None
        
        # Create the matplotlib figure and axis
        self.fig = Figure(figsize=(10, 5))  # Use Figure instead of plt.figure()
        self.ax1 = self.fig.add_subplot(121)  # Time series subplot
        self.ax2 = self.fig.add_subplot(122, projection='3d')  # 3D subplot

        # Time series data
        self.line = self.ax1.plot(self.dist, label='Distance between two coil midpoints')
        self.current_time_line = self.ax1.axvline(self.current_frame, color='k', linestyle='--', linewidth=1)
        self.ax1.set_title('Time Series Plot')
        self.ax1.set_xlabel('Time (samples)')
        self.ax1.set_ylabel('Distance (mm)')
        self.ax1.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0)).set_zorder(10)

        # 3D scatter plot data
        self.scat1 = self.ax2.scatter(self.head[0,0,:], self.head[0,1,:], self.head[0,2,:], c='r', marker='*', label='Head Markers')
        self.scat2 = self.ax2.scatter(self.coil[0,0,:], self.coil[0,1,:], self.coil[0,2,:], c='b', marker='*', label='Coil Markers')
        self.scat3 = self.ax2.scatter(self.headstimpoint[0,0,:], self.headstimpoint[0,1,:], self.headstimpoint[0,2,:], c='r', marker='o', label='Head stimpoint')
        self.scat4 = self.ax2.scatter(self.coilstimpoint[0,0,:], self.coilstimpoint[0,1,:], self.coilstimpoint[0,2,:], c='b', marker='o', label='Coil stimpoint')
        self.marker_texts = []
        self._create_marker_texts()
        
        set_axes_equal(self.ax2)
        # self.scat3 = self.ax2.scatter(self.x3d + 0.2, self.y3d + 0.2, self.z3d + 0.2, c='b', marker='^', label='Data Set 3')
       
        self.ax2.set_title('3D Scatter Plot')
        self.ax2.set_xlabel('X')
        self.ax2.set_ylabel('Y')
        self.ax2.set_zlabel('Z')
        self.ax2.legend(loc="upper right", bbox_to_anchor=(0.98, 0.98))

        # Create a canvas to embed the plot in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack()

        # Create Play and Pause buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack()
        
        self.play_button = ttk.Button(button_frame, text="Play", command=self.play)
        self.play_button.pack(side=tk.LEFT)
        
        self.pause_button = ttk.Button(button_frame, text="Pause", command=self.pause)
        self.pause_button.pack(side=tk.LEFT)

        self.distance_text = tk.StringVar(master=self.root)
        self.distance_label = ttk.Label(button_frame, textvariable=self.distance_text)
        self.distance_label.pack(side=tk.LEFT, padx=(12, 0))
        self._update_distance_label()

        self.show_marker_names = tk.BooleanVar(master=self.root, value=False)
        self.marker_names_checkbox = ttk.Checkbutton(
            button_frame,
            text="marker names",
            variable=self.show_marker_names,
            command=self._toggle_marker_names)
        self.marker_names_checkbox.pack(side=tk.LEFT, padx=(12, 0))
        
        # Create a slider to scroll through the animation
        self.slider = ttk.Scale(self.root, from_=0, to=self.num_frames-1, orient=tk.HORIZONTAL, command=self.slider_update)
        self.slider.pack(fill=tk.X)
        
        if self.live_mode:
            self.play()

        if auto_mainloop and self._owns_mainloop:
            self.root.mainloop()

    def on_close(self):
        if self.closed:
            return
        self.closed = True
        self.pause()
        if self.on_close_callback is not None:
            self.on_close_callback()
        if self.root.winfo_exists():
            self.root.destroy()

    def _compute_dist(self):
        return self.coilstimpoint[:, :, 0] - self.headstimpoint[:, :, 0]

    def _compute_euclidean_distance(self, frame):
        displacement = self.coilstimpoint[frame, :, 0] - self.headstimpoint[frame, :, 0]
        return np.linalg.norm(displacement)

    def _update_distance_label(self):
        distance = self._compute_euclidean_distance(self.current_frame)
        self.distance_text.set(f"eucledian distance: {distance:.2f} mm")

    def _create_marker_texts(self):
        for marker_index, name in enumerate(self.headmarkernames[:self.head.shape[2]]):
            text = self.ax2.text(
                self.head[0, 0, marker_index],
                self.head[0, 1, marker_index],
                self.head[0, 2, marker_index],
                name,
                color='r',
                visible=False)
            self.marker_texts.append((text, "head", marker_index))

        for marker_index, name in enumerate(self.coilmarkernames[:self.coil.shape[2]]):
            text = self.ax2.text(
                self.coil[0, 0, marker_index],
                self.coil[0, 1, marker_index],
                self.coil[0, 2, marker_index],
                name,
                color='b',
                visible=False)
            self.marker_texts.append((text, "coil", marker_index))

    def _toggle_marker_names(self):
        show_names = self.show_marker_names.get()
        for text, _, _ in self.marker_texts:
            text.set_visible(show_names)
        if show_names:
            self._update_marker_texts()
        self.canvas.draw_idle()

    def _update_marker_texts(self):
        if not self.show_marker_names.get():
            return
        for text, marker_group, marker_index in self.marker_texts:
            data = self.head if marker_group == "head" else self.coil
            text.set_position((data[self.current_frame, 0, marker_index],
                               data[self.current_frame, 1, marker_index]))
            text.set_3d_properties(data[self.current_frame, 2, marker_index], zdir='z')

    def _refresh_timeseries(self):
        self.dist = self._compute_dist()
        x = np.arange(self.dist.shape[0])
        for index, line in enumerate(self.line):
            line.set_data(x, self.dist[:, index])
        self.ax1.relim()
        self.ax1.autoscale_view()
    def play(self):
        if not self.is_paused:
            return
        self.is_paused = False
        self._schedule_next_frame()
    
    def pause(self):
        self.is_paused = True
        if self.after_job is not None:
            self.root.after_cancel(self.after_job)
            self.after_job = None

    def _schedule_next_frame(self):
        if self.is_paused or self.after_job is not None:
            return
        self.after_job = self.root.after(self.frame_interval_ms, self._tick)

    def _tick(self):
        self.after_job = None
        if self.is_paused:
            return
        self.update_plot(self.current_frame)
        self.canvas.draw_idle()
        if not self.is_paused:
            self.current_frame += 1
            self._schedule_next_frame()

    def slider_update(self, val):
        if not self.slider_moving:  # Avoid recursion by checking if the slider is manually moved
            self.slider_moving = True
            self.current_frame = int(float(val))
            self.update_plot(self.current_frame, force_distance_update=True)
            self.canvas.draw_idle()
            self.slider_moving = False

    def update_plot(self, frame, force_distance_update=False):
        if self.num_frames == 0:
            return self.line

        if frame >= self.num_frames:
            frame = self.num_frames - 1
            if not self.live_mode:
                self.pause()

        if not self.slider_moving and (
            frame == 0
            or frame == self.num_frames - 1
            or frame % self.slider_update_stride == 0
        ):
            self.slider_moving = True  # Temporarily disable slider update
            self.slider.set(frame)
            self.slider_moving = False  # Re-enable slider update
            
        self.current_frame = frame
        # Update time series plot
        # self.line.set_ydata(np.sin(self.x + 2 * np.pi * self.current_frame / self.num_frames))
        self.current_time_line.set_xdata([self.current_frame, self.current_frame])
        if (force_distance_update or
                self.current_frame == 0 or
                self.current_frame == self.num_frames - 1 or
                self.current_frame % self.distance_update_stride == 0):
            self._update_distance_label()
        
        #  # Update 3D scatter plot
        self.scat1._offsets3d = (self.head [self.current_frame,0,:], self.head [self.current_frame,1,:], self.head [self.current_frame,2,:])
        self.scat2._offsets3d = (self.coil [self.current_frame,0,:], self.coil [self.current_frame,1,:], self.coil [self.current_frame,2,:])
        self.scat3._offsets3d = (self.headstimpoint [self.current_frame,0,:], self.headstimpoint [self.current_frame,1,:], self.headstimpoint [self.current_frame,2,:])
        self.scat4._offsets3d = (self.coilstimpoint [self.current_frame,0,:], self.coilstimpoint [self.current_frame,1,:], self.coilstimpoint [self.current_frame,2,:])
        self._update_marker_texts()
        
        return self.line#, self.scat1, self.scat2, self.scat3

    def append_frame(self, coildatastruct):
        """
        Append one live frame and redraw the existing animation window.
        """
        self.append_frames([coildatastruct])

    def append_frames(self, coildatastructs):
        """
        Append multiple live frames and redraw once.
        """
        if len(coildatastructs) == 0:
            return

        self.head = np.concatenate([self.head] + [frame["headexpdata"] for frame in coildatastructs], axis=0)
        self.coil = np.concatenate([self.coil] + [frame["coilexpdata"] for frame in coildatastructs], axis=0)
        self.headstimpoint = np.concatenate(
            [self.headstimpoint] + [frame["headstimpoint"] for frame in coildatastructs],
            axis=0,
        )
        self.coilstimpoint = np.concatenate(
            [self.coilstimpoint] + [frame["coilstimpoint"] for frame in coildatastructs],
            axis=0,
        )

        if self.live_mode and self.head.shape[0] > self.live_history_limit:
            self.head = self.head[-self.live_history_limit:]
            self.coil = self.coil[-self.live_history_limit:]
            self.headstimpoint = self.headstimpoint[-self.live_history_limit:]
            self.coilstimpoint = self.coilstimpoint[-self.live_history_limit:]

        self.num_frames = self.head.shape[0]
        self.slider.configure(to=self.num_frames - 1)
        self.current_frame = self.num_frames - 1
        self._refresh_timeseries()
        self.update_plot(self.current_frame, force_distance_update=True)
        # self.canvas.draw_idle()
    
    
def set_axes_equal(ax):
    """Set 3D plot axes to equal scale."""
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    y_range = abs(y_limits[1] - y_limits[0])
    z_range = abs(z_limits[1] - z_limits[0])

    max_range = max([x_range, y_range, z_range])

    mid_x = np.mean(x_limits)
    mid_y = np.mean(y_limits)
    mid_z = np.mean(z_limits)

    ax.set_xlim3d([mid_x - max_range / 2, mid_x + max_range / 2])
    ax.set_ylim3d([mid_y - max_range / 2, mid_y + max_range / 2])
    ax.set_zlim3d([mid_z - max_range / 2, mid_z + max_range / 2])
    
    
    
    
    
    
    
    
