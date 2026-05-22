#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog

import numpy as np
from ezc3d import c3d

try:
    from pylsl import StreamInfo, StreamOutlet, local_clock
except ImportError:  # pragma: no cover - depends on local environment
    StreamInfo = None
    StreamOutlet = None
    local_clock = None


def normalize_marker_names(marker_names, expected_count):
    """Normalize raw C3D marker labels to a fixed number of usable names.

    Parameters
    ----------
    marker_names : sequence
        Raw marker labels read from C3D metadata.
    expected_count : int
        Number of marker labels required by the point data.

    Returns
    -------
    list of str
        Trimmed marker names with generated ``Marker_N`` fallbacks for missing
        or empty labels.
    """
    normalized_names = []
    for index in range(expected_count):
        raw_name = marker_names[index] if index < len(marker_names) else ""
        name = str(raw_name).strip()
        if not name:
            name = f"Marker_{index + 1}"
        normalized_names.append(name)
    return normalized_names


def load_c3d_stream_data(filename):
    """Load point data, marker names, and frame rate from a C3D file.

    Parameters
    ----------
    filename : str
        Path to the C3D file to stream.

    Returns
    -------
    tuple
        ``(point_data, marker_names, frame_rate)`` where ``point_data`` is a
        ``3 x n_markers x n_frames`` coordinate array, ``marker_names`` are
        normalized labels, and ``frame_rate`` is the POINT sampling rate.
    """
    c3d_data = c3d(filename)
    point_data = c3d_data["data"]["points"][0:3, :, :]
    raw_marker_names = list(c3d_data["parameters"]["POINT"]["LABELS"]["value"])
    marker_names = normalize_marker_names(raw_marker_names, point_data.shape[1])
    frame_rate = float(c3d_data["parameters"]["POINT"]["RATE"]["value"][0])
    return point_data, marker_names, frame_rate


def add_marker_metadata(description, marker_names):
    """Append marker and channel metadata to an LSL stream description.

    Parameters
    ----------
    description : pylsl.XMLElement
        Mutable LSL description node returned by ``StreamInfo.desc()``.
    marker_names : list of str
        Marker labels to expose in stream metadata.

    Returns
    -------
    None.
        Mutates ``description`` by adding ``markers`` and ``channels`` nodes
        with XYZ channel labels and units.
    """
    markers = description.append_child("markers")
    for marker_name in marker_names:
        marker = markers.append_child("marker")
        marker.append_child_value("label", marker_name)

    channels = description.append_child("channels")
    for marker_name in marker_names:
        for axis in ("X", "Y", "Z"):
            channel = channels.append_child("channel")
            channel.append_child_value("label", marker_name)
            channel.append_child_value("marker", marker_name)
            channel.append_child_value("name", f"{marker_name}_{axis}")
            channel.append_child_value("axis", axis)
            channel.append_child_value("unit", "mm")


def create_marker_stream_info(stream_name, frame_rate, marker_names):
    """Create LSL stream metadata for streaming 3D marker coordinates.

    Parameters
    ----------
    stream_name : str
        Name advertised for the LSL stream.
    frame_rate : float
        Sampling rate in frames per second.
    marker_names : list of str
        Marker labels; each marker contributes X, Y, and Z channels.

    Returns
    -------
    pylsl.StreamInfo
        Configured stream info with channel count and marker metadata.
    """
    if StreamInfo is None:
        raise RuntimeError("LSL support is unavailable. Install 'pylsl' first.")

    info = StreamInfo(
        stream_name,
        "Markers",
        len(marker_names) * 3,
        frame_rate,
        "float32",
        f"{stream_name}_source",
    )
    add_marker_metadata(info.desc(), marker_names)
    return info


class C3DToLSLStreamer:
    """Tkinter app that replays C3D marker coordinates as an LSL stream.

    The app loads C3D point data into memory, creates marker-aware LSL stream
    metadata, and pushes one flattened XYZ frame per timer tick at the C3D frame
    rate.
    """

    def __init__(self):
        """Initialize stream state, build the Tk GUI, and start the event loop.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Stores loaded C3D data and streaming state on the instance while the
            user controls playback.
        """
        self.filename = None
        self.point_data = None
        self.marker_names = []
        self.frame_rate = 120.0
        self.current_frame = 0
        self.next_push_time = None
        self.outlet = None
        self.stream_info = None
        self.streaming = False

        self.root = tk.Tk()
        self.root.title("C3D to LSL Streamer")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.loop_playback = tk.BooleanVar(master=self.root, value=True)
        self.stream_name_var = tk.StringVar(master=self.root, value="C3DMarkers")

        self.file_btn = tk.Button(self.root, text="Select C3D File", command=self.select_file)
        self.file_btn.grid(row=0, column=0, padx=10, pady=10)

        self.file_label = tk.Label(self.root, text="No file selected", width=55, anchor="w")
        self.file_label.grid(row=0, column=1, columnspan=2, padx=10, pady=10, sticky="ew")

        self.stream_name_label = tk.Label(self.root, text="Stream name")
        self.stream_name_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.stream_name_entry = tk.Entry(self.root, textvariable=self.stream_name_var, width=30)
        self.stream_name_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.loop_checkbox = tk.Checkbutton(self.root, text="Loop playback", variable=self.loop_playback)
        self.loop_checkbox.grid(row=1, column=2, padx=10, pady=10, sticky="w")

        self.start_btn = tk.Button(self.root, text="Start Streaming", command=self.start_streaming)
        self.start_btn.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.stop_btn = tk.Button(self.root, text="Stop Streaming", command=self.stop_streaming)
        self.stop_btn.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.status_label = tk.Label(self.root, text="Select a C3D file to begin.", anchor="w", justify="left")
        self.status_label.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        self.root.mainloop()

    def set_status(self, message):
        """Show the current loading or streaming state in the GUI.

        Parameters
        ----------
        message : str
            Status text to display.

        Returns
        -------
        None.
            Updates only the status label.
        """
        self.status_label.config(text=message)

    def select_file(self):
        """Select and load a C3D file for streaming.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.filename``, ``self.point_data``,
            ``self.marker_names``, ``self.frame_rate``, and resets
            ``self.current_frame``.
        """
        filename = filedialog.askopenfilename(filetypes=[("C3D files", "*.c3d"), ("All files", "*.*")])
        if not filename:
            return

        self.filename = filename
        self.point_data, self.marker_names, self.frame_rate = load_c3d_stream_data(filename)
        self.current_frame = 0

        self.file_label.config(text=filename)
        self.set_status(
            f"Loaded {self.point_data.shape[2]} frames, {self.point_data.shape[1]} markers at {self.frame_rate:.2f} Hz."
        )

    def start_streaming(self):
        """Start broadcasting loaded C3D marker frames over LSL.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Creates stream metadata and an outlet, resets timing/frame state,
            marks streaming active, and schedules the first frame push.
        """
        if StreamInfo is None:
            self.set_status("LSL support is unavailable. Install 'pylsl' first.")
            return
        if self.point_data is None:
            self.select_file()
        if self.point_data is None:
            self.set_status("No C3D file loaded.")
            return

        self.stream_info = self._create_stream_info()
        self.outlet = StreamOutlet(self.stream_info)
        self.streaming = True
        self.current_frame = 0
        self.next_push_time = local_clock()
        self.set_status(f"Streaming '{self.stream_name_var.get()}' over LSL.")
        self._schedule_next_frame()

    def stop_streaming(self):
        """Stop the LSL replay and clear transient stream objects.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Sets streaming false and clears the outlet, stream info, and next
            push timestamp.
        """
        self.streaming = False
        self.outlet = None
        self.stream_info = None
        self.next_push_time = None
        self.set_status("Streaming stopped.")

    def _create_stream_info(self):
        """Build LSL stream metadata from the current GUI settings.

        Parameters
        ----------
        None.

        Returns
        -------
        pylsl.StreamInfo
            Marker stream information using the current stream name, frame rate,
            and marker labels.
        """
        stream_name = self.stream_name_var.get().strip() or "C3DMarkers"
        return create_marker_stream_info(stream_name, self.frame_rate, self.marker_names)

    def _schedule_next_frame(self):
        """Schedule the next frame push if streaming is active.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Registers a Tk ``after`` callback to call ``push_next_frame``.
        """
        if not self.streaming:
            return
        self.root.after(1, self.push_next_frame)

    def push_next_frame(self):
        """Push the next C3D frame to the LSL outlet at playback timing.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Flattens the current ``3 x n_markers`` frame into XYZ channel order,
            sends it to LSL, advances or loops ``self.current_frame``, updates
            timing, and schedules the next push.
        """
        if not self.streaming or self.outlet is None or self.point_data is None:
            return

        now = local_clock()
        if now < self.next_push_time:
            delay_ms = max(int((self.next_push_time - now) * 1000), 1)
            self.root.after(delay_ms, self.push_next_frame)
            return

        frame = self.point_data[:, :, self.current_frame].T.reshape(-1).astype(np.float32)
        self.outlet.push_sample(frame.tolist(), timestamp=now)

        self.current_frame += 1
        if self.current_frame >= self.point_data.shape[2]:
            if self.loop_playback.get():
                self.current_frame = 0
            else:
                self.stop_streaming()
                return

        self.next_push_time += 1.0 / self.frame_rate
        self.set_status(
            f"Streaming '{self.stream_name_var.get()}' over LSL. Frame {self.current_frame + 1}/{self.point_data.shape[2]}."
        )
        self._schedule_next_frame()

    def on_close(self):
        """Close the streamer GUI and stop any active LSL stream.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Stops streaming, releases transient stream objects, and destroys the
            Tk root window.
        """
        self.stop_streaming()
        self.root.destroy()


if __name__ == "__main__":
    C3DToLSLStreamer()
