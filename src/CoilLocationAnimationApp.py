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
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure  # Import Figure

class AnimationApp:
    """
    A class representing an animation application.
    Attributes:
        root (tkinter.Tk): The root window of the application.
        head (numpy.ndarray): The head reference data.
        helmet (numpy.ndarray): The helmet reference data.
        headstimpoint (numpy.ndarray): The head stimulation point data.
        helmetstimpoint (numpy.ndarray): The helmet stimulation point data.
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
        scat2 (mpl_toolkits.mplot3d.art3d.Path3DCollection): The scatter plot for helmet markers.
        scat3 (mpl_toolkits.mplot3d.art3d.Path3DCollection): The scatter plot for head stimulation points.
        scat4 (mpl_toolkits.mplot3d.art3d.Path3DCollection): The scatter plot for helmet stimulation points.
        canvas (matplotlib.backends.backend_tkagg.FigureCanvasTkAgg): The canvas for embedding the plot in Tkinter.
        play_button (ttk.Button): The button for playing the animation.
        pause_button (ttk.Button): The button for pausing the animation.
        slider (ttk.Scale): The slider for scrolling through the animation.
        anim (matplotlib.animation.FuncAnimation): The animation object.
    Methods:
        __init__(self, coildatastruct): Initializes the AnimationApp object.
        play(self): Plays the animation.
        pause(self): Pauses the animation.
        frame_generator(self): Custom frame generator that starts from the current_frame.
        slider_update(self, val): Updates the animation plot based on the slider value.
        update_plot(self, frame): Updates the time series plot and 3D scatter plot.
    """

    def __init__(self,coildatastruct):
        self.root =  tk.Tk()
        self.root.title("Animation with Play/Pause and Slider")

        #data 
        self.head=coildatastruct["headrefdata"]
        self.helmet=coildatastruct["helmetrefdata"]
        self.headstimpoint=coildatastruct["headstimpoint"]
        self.helmetstimpoint=coildatastruct["helmetstimpoint"]
        self.dist=coildatastruct["helmetstimpoint"][:,:,0]-coildatastruct["headstimpoint"][:,:,0]

        # Initialize variables
        self.is_paused = True
        self.current_frame = 0
        self.num_frames = np.shape(self.head)[0]
        self.slider_moving = False  # Flag to prevent recursive slider updates
        
        # Create the matplotlib figure and axis
        self.fig = Figure(figsize=(10, 5))  # Use Figure instead of plt.figure()
        self.ax1 = self.fig.add_subplot(121)  # Time series subplot
        self.ax2 = self.fig.add_subplot(122, projection='3d')  # 3D subplot

        # Time series data
        self.line= self.ax1.plot(self.dist, label='Distance between two coil midpoints')
        self.ax1.set_title('Time Series Plot')
        self.ax1.set_xlabel('Time (samples)')
        self.ax1.set_ylabel('Distance (mm)')
        self.ax1.legend()

        # 3D scatter plot data
        self.scat1 = self.ax2.scatter(self.head[0,0,:], self.head[0,1,:], self.head[0,2,:], c='r', marker='*', label='Head Markers')
        self.scat2 = self.ax2.scatter(self.helmet[0,0,:], self.helmet[0,1,:], self.helmet[0,2,:], c='b', marker='*', label='Helmet Markers')
        self.scat3 = self.ax2.scatter(self.headstimpoint[0,0,:], self.headstimpoint[0,1,:], self.headstimpoint[0,2,:], c='r', marker='o', label='Head stimpoint')
        self.scat4 = self.ax2.scatter(self.helmetstimpoint[0,0,:], self.helmetstimpoint[0,1,:], self.helmetstimpoint[0,2,:], c='b', marker='o', label='Helmet stimpoint')
        
        set_axes_equal(self.ax2)
        # self.scat3 = self.ax2.scatter(self.x3d + 0.2, self.y3d + 0.2, self.z3d + 0.2, c='b', marker='^', label='Data Set 3')
       
        self.ax2.set_title('3D Scatter Plot')
        self.ax2.set_xlabel('X')
        self.ax2.set_ylabel('Y')
        self.ax2.set_zlabel('Z')
        self.ax2.legend()

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
        
        # Create a slider to scroll through the animation
        self.slider = ttk.Scale(self.root, from_=0, to=self.num_frames-1, orient=tk.HORIZONTAL, command=self.slider_update)
        self.slider.pack(fill=tk.X)
        
        # Initialize animation
        self.anim = FuncAnimation(self.fig, self.update_plot, frames=self.frame_generator, interval=50, blit=False, repeat=False)

        self.root.mainloop()
    def play(self):
        if self.is_paused:
            self.is_paused = False
            self.anim.event_source.start()
    
    def pause(self):
        if not self.is_paused:
            self.is_paused = True
            self.anim.event_source.stop()
            
    def frame_generator(self):
    #"""Custom frame generator that starts from the current_frame."""
        while True:
            yield self.current_frame
            if not self.is_paused:
                self.current_frame += 1
    def slider_update(self, val):
        if not self.slider_moving:  # Avoid recursion by checking if the slider is manually moved
            self.slider_moving = True
            self.current_frame = int(float(val))
            self.update_plot(self.current_frame)
            self.canvas.draw()
            self.slider_moving = False

    def update_plot(self, frame):
        if not self.slider_moving:#self.is_paused:         
            self.slider_moving = True  # Temporarily disable slider update
            self.slider.set(self.current_frame)
            self.slider_moving = False  # Re-enable slider update
            
        self.current_frame = frame
        # Update time series plot
        # self.line.set_ydata(np.sin(self.x + 2 * np.pi * self.current_frame / self.num_frames))
        
        #  # Update 3D scatter plot
        self.scat1._offsets3d = (self.head [self.current_frame,0,:], self.head [self.current_frame,1,:], self.head [self.current_frame,2,:])
        self.scat2._offsets3d = (self.helmet [self.current_frame,0,:], self.helmet [self.current_frame,1,:], self.helmet [self.current_frame,2,:])
        self.scat3._offsets3d = (self.headstimpoint [self.current_frame,0,:], self.headstimpoint [self.current_frame,1,:], self.headstimpoint [self.current_frame,2,:])
        self.scat4._offsets3d = (self.helmetstimpoint [self.current_frame,0,:], self.helmetstimpoint [self.current_frame,1,:], self.helmetstimpoint [self.current_frame,2,:])
        
        return self.line#, self.scat1, self.scat2, self.scat3
    
    
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
    
    
    
    
    
    
    
    
