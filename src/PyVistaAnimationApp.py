#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyVista/Qt animation app for coil location visualization.

This module intentionally exports an AnimationApp class with the same public
entry points as CoilLocationAnimationApp.AnimationApp, so callers can switch
between backends by changing the import.
"""

import numpy as np

try:
    import pyvista as pv
    try:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    except ImportError:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from pyvistaqt import QtInteractor
    from qtpy import QtCore, QtWidgets
except ImportError as exc:  # pragma: no cover - depends on optional GUI deps
    pv = None
    FigureCanvas = None
    Figure = None
    QtInteractor = None
    QtCore = None
    QtWidgets = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class AnimationApp:
    """
    PyVista/Qt animation app with the same interface as the Matplotlib version.
    """

    def __init__(self, coildatastruct, master=None, auto_mainloop=True,
                 live_mode=False, on_close_callback=None):
        if _IMPORT_ERROR is not None:
            raise ImportError(
                "PyVistaAnimationApp requires pyvista, pyvistaqt, and a Qt binding "
                "such as PyQt5. Install them to use this backend."
            ) from _IMPORT_ERROR

        self.live_mode = live_mode
        self._owns_mainloop = master is None
        self.master = master
        self.on_close_callback = on_close_callback
        self.closed = False
        self.qt_event_pump_job = None

        self.head = np.array(coildatastruct["headexpdata"], copy=True)
        self.coil = np.array(coildatastruct["coilexpdata"], copy=True)
        self.headstimpoint = np.array(coildatastruct["headstimpoint"], copy=True)
        self.coilstimpoint = np.array(coildatastruct["coilstimpoint"], copy=True)
        self.headmarkernames = list(coildatastruct.get("headmarkernames", []))
        self.coilmarkernames = list(coildatastruct.get("coilmarkernames", []))

        self.current_frame = 0
        self.num_frames = max(self.head.shape[0], 1)
        self.is_paused = True
        self.slider_moving = False
        self.live_history_limit = 500
        self.slider_update_stride = 5
        self.distance_update_stride = 10
        self.frame_interval_ms = 10
        self.show_marker_names = False
        self.dist = self._compute_dist()

        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])

        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle("Coil Location Animation")
        self.window.resize(1200, 650)

        central_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(splitter)

        self.figure = Figure(figsize=(5, 5))
        self.ax1 = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        splitter.addWidget(self.canvas)

        self.plotter = QtInteractor(central_widget)
        splitter.addWidget(self.plotter)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        self.window.setCentralWidget(central_widget)
        self.plotter.set_background("white")
        self.plotter.add_axes()
        self._update_bounds_box()

        self.line = self.ax1.plot(self.dist, label="Distance between two coil midpoints")
        self.current_time_line = self.ax1.axvline(
            self.current_frame,
            color="k",
            linestyle="--",
            linewidth=1,
        )
        self.ax1.set_title("Time Series Plot")
        self.ax1.set_xlabel("Time (samples)")
        self.ax1.set_ylabel("Distance (mm)")
        self.ax1.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0)).set_zorder(10)

        self.head_poly = pv.PolyData(self._frame_points(self.head))
        self.coil_poly = pv.PolyData(self._frame_points(self.coil))
        self.headstim_poly = pv.PolyData(self._frame_points(self.headstimpoint))
        self.coilstim_poly = pv.PolyData(self._frame_points(self.coilstimpoint))

        self.plotter.add_points(
            self.head_poly,
            color="red",
            point_size=12,
            render_points_as_spheres=True,
            name="head_markers",
        )
        self.plotter.add_points(
            self.coil_poly,
            color="blue",
            point_size=12,
            render_points_as_spheres=True,
            name="coil_markers",
        )
        self.plotter.add_points(
            self.headstim_poly,
            color="darkred",
            point_size=18,
            render_points_as_spheres=True,
            name="head_stimpoint",
        )
        self.plotter.add_points(
            self.coilstim_poly,
            color="navy",
            point_size=18,
            render_points_as_spheres=True,
            name="coil_stimpoint",
        )
        self._add_links()
        self.plotter.add_legend([
            ["Head markers", "red"],
            ["Coil markers", "blue"],
            ["Head stimpoint", "darkred"],
            ["Coil stimpoint", "navy"],
        ])

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._tick)

        self.slider = None
        self.distance_label = None
        self.marker_names_checkbox = None
        self._build_qt_controls()
        self._install_close_handler()
        self._update_distance_label()
        self.update_plot(self.current_frame, force_distance_update=True)
        self.plotter.reset_camera()
        self.window.show()
        self._start_qt_event_pump()

        if self.live_mode:
            self.play()

        if auto_mainloop and self._owns_mainloop:
            self.app.exec_()

    def _remove_actor(self, name):
        try:
            self.plotter.remove_actor(name, render=False)
        except (KeyError, ValueError, TypeError):
            pass

    def _scene_bounds(self):
        points = np.vstack([
            self.head.transpose(0, 2, 1).reshape(-1, 3),
            self.coil.transpose(0, 2, 1).reshape(-1, 3),
            self.headstimpoint.transpose(0, 2, 1).reshape(-1, 3),
            self.coilstimpoint.transpose(0, 2, 1).reshape(-1, 3),
        ])
        points = points[~np.isnan(points).any(axis=1)]
        if points.size == 0:
            return (-1, 1, -1, 1, -1, 1)

        mins = np.min(points, axis=0)
        maxs = np.max(points, axis=0)
        span = np.max(maxs - mins)
        if span == 0:
            span = 1
        padding = span * 0.15
        return (
            mins[0] - padding, maxs[0] + padding,
            mins[1] - padding, maxs[1] + padding,
            mins[2] - padding, maxs[2] + padding,
        )

    def _update_bounds_box(self):
        self.plotter.show_bounds(
            bounds=self._scene_bounds(),
            grid="back",
            location="outer",
            all_edges=True,
            color="black",
            font_size=10,
            xlabel="X",
            ylabel="Y",
            zlabel="Z",
        )

    def _start_qt_event_pump(self):
        if self.master is not None and hasattr(self.master, "after"):
            self._pump_qt_events()

    def _pump_qt_events(self):
        if self.closed:
            self.qt_event_pump_job = None
            return
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.processEvents()
        self.qt_event_pump_job = self.master.after(10, self._pump_qt_events)

    def _stop_qt_event_pump(self):
        if self.qt_event_pump_job is not None and self.master is not None:
            try:
                self.master.after_cancel(self.qt_event_pump_job)
            except Exception:
                pass
            self.qt_event_pump_job = None

    def _frame_points(self, data, frame=None):
        if frame is None:
            frame = self.current_frame
        return np.asarray(data[frame, :, :]).T

    def _build_qt_controls(self):
        toolbar = QtWidgets.QToolBar("Animation")
        play_action = toolbar.addAction("Play")
        play_action.triggered.connect(self.play)
        pause_action = toolbar.addAction("Pause")
        pause_action.triggered.connect(self.pause)

        toolbar.addSeparator()
        self.distance_label = QtWidgets.QLabel()
        toolbar.addWidget(self.distance_label)

        toolbar.addSeparator()
        self.marker_names_checkbox = QtWidgets.QCheckBox("marker names")
        self.marker_names_checkbox.stateChanged.connect(self._toggle_marker_names)
        toolbar.addWidget(self.marker_names_checkbox)

        toolbar.addSeparator()
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(max(self.num_frames - 1, 0))
        self.slider.setValue(self.current_frame)
        self.slider.setMinimumWidth(240)
        self.slider.valueChanged.connect(self.slider_update)
        toolbar.addWidget(self.slider)

        self.window.addToolBar(toolbar)

    def _install_close_handler(self):
        original_close_event = self.window.closeEvent

        def close_event(event):
            if not self.closed:
                self.closed = True
                self.pause()
                self._stop_qt_event_pump()
                if self.on_close_callback is not None:
                    self.on_close_callback()
            original_close_event(event)

        self.window.closeEvent = close_event

    def _add_links(self):
        self._remove_actor("stimpoint_link")
        points = np.vstack([
            self._frame_points(self.headstimpoint),
            self._frame_points(self.coilstimpoint),
        ])
        if points.shape[0] == 2:
            line = pv.Line(points[0], points[1])
            self.plotter.add_mesh(line, color="black", line_width=2, name="stimpoint_link")

    def _compute_euclidean_distance(self, frame):
        displacement = self.coilstimpoint[frame, :, 0] - self.headstimpoint[frame, :, 0]
        return np.linalg.norm(displacement)

    def _compute_dist(self):
        return self.coilstimpoint[:, :, 0] - self.headstimpoint[:, :, 0]

    def _update_distance_label(self):
        text = f"eucledian distance: {self._compute_euclidean_distance(self.current_frame):.2f} mm"
        if self.distance_label is not None:
            self.distance_label.setText(text)

    def _refresh_timeseries(self):
        self.dist = self._compute_dist()
        x = np.arange(self.dist.shape[0])
        for index, line in enumerate(self.line):
            line.set_data(x, self.dist[:, index])
        self.ax1.relim()
        self.ax1.autoscale_view()

    def _marker_label_points_and_names(self):
        head_names = self.headmarkernames[:self.head.shape[2]]
        coil_names = self.coilmarkernames[:self.coil.shape[2]]
        points = []
        labels = []

        if len(head_names) > 0:
            points.append(self._frame_points(self.head)[:len(head_names)])
            labels.extend(head_names)
        if len(coil_names) > 0:
            points.append(self._frame_points(self.coil)[:len(coil_names)])
            labels.extend(coil_names)

        if len(points) == 0:
            return np.empty((0, 3)), []
        return np.vstack(points), labels

    def _toggle_marker_names(self, *args):
        if self.marker_names_checkbox is not None:
            self.show_marker_names = self.marker_names_checkbox.isChecked()
        else:
            self.show_marker_names = not self.show_marker_names
        self._update_marker_labels()
        self.plotter.render()

    def _update_marker_labels(self):
        self._remove_actor("marker_labels")
        if not self.show_marker_names:
            return

        points, labels = self._marker_label_points_and_names()
        if len(labels) == 0:
            return
        self.plotter.add_point_labels(
            points,
            labels,
            font_size=12,
            text_color="black",
            shape_opacity=0.0,
            always_visible=True,
            name="marker_labels",
            render=False,
        )

    def play(self):
        if not self.is_paused:
            return
        self.is_paused = False
        self.timer.start(self.frame_interval_ms)

    def pause(self):
        self.is_paused = True
        self.timer.stop()

    def _tick(self):
        if self.is_paused:
            return
        self.update_plot(self.current_frame)
        if not self.is_paused:
            self.current_frame += 1

    def slider_update(self, value):
        if self.slider_moving:
            return
        self.slider_moving = True
        self.update_plot(int(value), force_distance_update=True)
        self.slider_moving = False

    def update_plot(self, frame, force_distance_update=False):
        if self.num_frames == 0 or self.closed:
            return

        if frame >= self.num_frames:
            frame = self.num_frames - 1
            if not self.live_mode:
                self.pause()
        if frame < 0:
            frame = 0

        self.current_frame = frame
        self.head_poly.points = self._frame_points(self.head)
        self.coil_poly.points = self._frame_points(self.coil)
        self.headstim_poly.points = self._frame_points(self.headstimpoint)
        self.coilstim_poly.points = self._frame_points(self.coilstimpoint)
        self.head_poly.Modified()
        self.coil_poly.Modified()
        self.headstim_poly.Modified()
        self.coilstim_poly.Modified()
        self._add_links()
        self.current_time_line.set_xdata([self.current_frame, self.current_frame])

        if self.slider is not None and not self.slider_moving and (
            frame == 0
            or frame == self.num_frames - 1
            or frame % self.slider_update_stride == 0
        ):
            self.slider_moving = True
            self.slider.setValue(frame)
            self.slider_moving = False

        if (force_distance_update or
                frame == 0 or
                frame == self.num_frames - 1 or
                frame % self.distance_update_stride == 0):
            self._update_distance_label()

        self._update_marker_labels()
        self.plotter.render()
        self.canvas.draw_idle()

    def append_frame(self, coildatastruct):
        self.append_frames([coildatastruct])

    def append_frames(self, coildatastructs):
        if len(coildatastructs) == 0 or self.closed:
            return

        self.head = np.concatenate(
            [self.head] + [frame["headexpdata"] for frame in coildatastructs],
            axis=0,
        )
        self.coil = np.concatenate(
            [self.coil] + [frame["coilexpdata"] for frame in coildatastructs],
            axis=0,
        )
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
        self.current_frame = self.num_frames - 1
        if self.slider is not None:
            self.slider.setMaximum(max(self.num_frames - 1, 0))
        self._refresh_timeseries()
        self._update_bounds_box()
        self.update_plot(self.current_frame, force_distance_update=True)

    def on_close(self):
        if self.closed:
            return
        self.closed = True
        self.pause()
        self._stop_qt_event_pump()
        if self.on_close_callback is not None:
            self.on_close_callback()
        self.plotter.close()
        self.window.close()
