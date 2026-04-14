import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
import tkinter as tk

class MarkerSelector:
    def __init__(self, markers, markernames,selected_markers_set1,selected_markers_set2,selected_markers_set3):
        # Create the tkinter window

        self.master = tk.Tk()
        self.master.title("Select Marker Sets")

        # Data
        self.markers = markers
        self.markernames = markernames
        self.n_markers = markers.shape[1]

        # State
        self.current_set = 1
        self.selected_markers_set1 = selected_markers_set1
        self.selected_markers_set2 = selected_markers_set2
        self.selected_markers_set3 = selected_markers_set3
        self.marker_colors = ['blue'] * self.n_markers
        
        for i_name in range(0,len(selected_markers_set1)):
            self.marker_colors[self.markernames.index(self.selected_markers_set1[i_name])]='red'           
        for i_name in range(0,len(selected_markers_set2)):
            self.marker_colors[self.markernames.index(self.selected_markers_set2[i_name])]='green'         
        for i_name in range(0,len(selected_markers_set3)):
            try:
                self.marker_colors[self.markernames.index(self.selected_markers_set3[i_name])]='purple'
            except:
                print('')
            

        # Initialize plot limits
        self.xlim = None
        self.ylim = None
        self.zlim = None

        # Figure and Canvas
        self.fig = plt.Figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.selected_text = self.ax.text2D(0.05, 0.95, '', transform=self.ax.transAxes)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.master)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Hide the toolbar
        self.toolbar.pack_forget()  # Hide the toolbar

        # Buttons 
        self.button1 = tk.Button(self.master, text="Select coil markers", command=self.select_set1, bg='red',fg='red')
        self.button1.pack(side=tk.LEFT)

        self.button2 = tk.Button(self.master, text="Select head markers", command=self.select_set2, bg='green',fg='green')
        self.button2.pack(side=tk.LEFT)

        self.button3 = tk.Button(self.master, text="Select stimulation marker", command=self.select_set3, bg='purple',fg='purple')
        self.button3.pack(side=tk.LEFT)

        self.zoom_button = tk.Button(self.master, text="Zoom", command=self.activate_zoom)
        self.zoom_button.pack(side=tk.LEFT)

        self.reset_zoom_button = tk.Button(self.master, text="Reset Zoom", command=self.reset_zoom)
        self.reset_zoom_button.pack(side=tk.LEFT)
        

        self.done_button = tk.Button(self.master, text="Done", command=self.done)
        self.done_button.pack(side=tk.BOTTOM, pady=10)

        # Plot initialization
        self.update_plot()

        # Event binding
        self.cid_pick = self.fig.canvas.mpl_connect('pick_event', self.onpick)
        self.cid_zoom = None

        # Initialize zoom state
        self.zoom_active = False
        self.master.protocol("WM_DELETE_WINDOW", self.done)

        # Run the tkinter main loop
        self.master.mainloop()
    def update_plot(self):
        """Updates the plot to display the marker coordinates."""
        # Store current limits before clearing
        if self.xlim is not None and self.ylim is not None and self.zlim is not None:
            self.xlim = self.ax.get_xlim()
            self.ylim = self.ax.get_ylim()
            self.zlim = self.ax.get_zlim()

        self.ax.clear()

        x, y, z = self.markers[0, :], self.markers[1, :], self.markers[2, :]
        self.sc = self.ax.scatter(x, y, z, c=self.marker_colors, picker=True)

        for i in range(self.n_markers):
            self.ax.text(x[i], y[i], z[i], self.markernames[i], fontsize=9)

        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_title('3D Marker Coordinates')

        # Reapply stored limits to maintain the zoom level
        if self.xlim is not None and self.ylim is not None and self.zlim is not None:
            self.ax.set_xlim(self.xlim)
            self.ax.set_ylim(self.ylim)
            self.ax.set_zlim(self.zlim)
            
        # Update the selected markers text in the plot
        # self.selected_text.set_text(
            # f'Selected Set 1: {", ".join(self.selected_markers_set1)}\n'
            # f'Selected Set 2: {", ".join(self.selected_markers_set2)}\n'
            # f'Selected Set 3: {", ".join(self.selected_markers_set3)}'
        # )
        set_axes_equal(self.ax)
        self.canvas.draw()

    def onpick(self, event):
        """Event handler for picking a marker."""
        if event.artist != self.sc:
            return

        indices = event.ind
        for i in indices:
            marker_name = self.markernames[i]
            if self.current_set == 1:
                if marker_name not in self.selected_markers_set1:
                    self.selected_markers_set1.append(marker_name)
                    self.marker_colors[i] = 'red'  # Set 1 color
                else:
                    self.selected_markers_set1.remove(marker_name)
                    self.marker_colors[i] = 'blue' if marker_name not in self.selected_markers_set2 + self.selected_markers_set3 else ('green' if marker_name in self.selected_markers_set2 else 'purple')
            elif self.current_set == 2:
                if marker_name not in self.selected_markers_set2:
                    self.selected_markers_set2.append(marker_name)
                    self.marker_colors[i] = 'green'  # Set 2 color
                else:
                    self.selected_markers_set2.remove(marker_name)
                    self.marker_colors[i] = 'blue' if marker_name not in self.selected_markers_set1 + self.selected_markers_set3 else ('red' if marker_name in self.selected_markers_set1 else 'purple')
            elif self.current_set == 3:
                if marker_name not in self.selected_markers_set3:
                    self.selected_markers_set3.append(marker_name)
                    self.marker_colors[i] = 'purple'  # Set 3 color
                else:
                    self.selected_markers_set3.remove(marker_name)
                    self.marker_colors[i] = 'blue' if marker_name not in self.selected_markers_set1 + self.selected_markers_set2 else ('red' if marker_name in self.selected_markers_set1 else 'green')
        
        # Update the plot to reflect the color change
        self.update_plot()

    def select_set1(self):
        self.current_set = 1

    def select_set2(self):
        self.current_set = 2

    def select_set3(self):
        self.current_set = 3

    def activate_zoom(self):
        """Activates zoom mode and stays zoomed after selection."""
        if not self.zoom_active:
            self.cid_zoom = self.fig.canvas.mpl_connect('button_release_event', self.lock_zoom)
            self.fig.canvas.toolbar.zoom()  # Use the toolbar's zoom method
            self.zoom_active = True

    def lock_zoom(self, event):
        """Keep the current zoom level locked after zoom."""
        self.fig.canvas.toolbar.zoom()  # Lock the zoom level by turning off the zoom tool

        # Store the current zoom level
        self.xlim = self.ax.get_xlim()
        self.ylim = self.ax.get_ylim()
        self.zlim = self.ax.get_zlim()

        # Disable zoom mode after the user zooms in
        self.fig.canvas.mpl_disconnect(self.cid_zoom)
        self.zoom_active = False

    def reset_zoom(self):
        """Resets the zoom to the original view."""
        self.ax.set_xlim(None)
        self.ax.set_ylim(None)
        self.ax.set_zlim(None)
        self.xlim = self.ylim = self.zlim = None
        self.update_plot()
        self.canvas.draw()
    def get_marker_names(self):
        return self.selected_markers_set1, self.selected_markers_set2, self.selected_markers_set3
    def done(self):
        plt.close(self.fig)
        self.master.quit()
        self.master.destroy()

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
# # Example data
# n_markers = 10  # Number of markers

# # Randomly generate 3D coordinates for demonstration purposes
# markers = np.random.rand(3, n_markers)
# markernames = [f'Marker_{i}' for i in range(n_markers)]  # Example marker names
# selected_markers_set1=[]
# selected_markers_set2=[]
# selected_markers_set3=['Marker_4']

# # Initialize the MarkerSelector object with the data
# app = MarkerSelector(markers, markernames,selected_markers_set1,selected_markers_set2,selected_markers_set3)
