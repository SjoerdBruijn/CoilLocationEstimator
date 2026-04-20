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
    normalized_names = []
    for index in range(expected_count):
        raw_name = marker_names[index] if index < len(marker_names) else ""
        name = str(raw_name).strip()
        if not name:
            name = f"Marker_{index + 1}"
        normalized_names.append(name)
    return normalized_names


def load_c3d_stream_data(filename):
    c3d_data = c3d(filename)
    point_data = c3d_data["data"]["points"][0:3, :, :]
    raw_marker_names = list(c3d_data["parameters"]["POINT"]["LABELS"]["value"])
    marker_names = normalize_marker_names(raw_marker_names, point_data.shape[1])
    frame_rate = float(c3d_data["parameters"]["POINT"]["RATE"]["value"][0])
    return point_data, marker_names, frame_rate


def add_marker_metadata(description, marker_names):
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
    def __init__(self):
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
        self.status_label.config(text=message)

    def select_file(self):
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
        self.streaming = False
        self.outlet = None
        self.stream_info = None
        self.next_push_time = None
        self.set_status("Streaming stopped.")

    def _create_stream_info(self):
        stream_name = self.stream_name_var.get().strip() or "C3DMarkers"
        return create_marker_stream_info(stream_name, self.frame_rate, self.marker_names)

    def _schedule_next_frame(self):
        if not self.streaming:
            return
        self.root.after(1, self.push_next_frame)

    def push_next_frame(self):
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
        self.stop_streaming()
        self.root.destroy()


if __name__ == "__main__":
    C3DToLSLStreamer()
