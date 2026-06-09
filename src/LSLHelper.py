#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unified LSL helper module.

This module combines:
- marker-name viewer GUI
- marker-name CLI utility
- C3D-to-LSL streamer GUI
"""

import argparse
import sys
import tkinter as tk
from tkinter import filedialog

import numpy as np
from ezc3d import c3d

try:
    from pylsl import StreamInfo, StreamInlet, StreamOutlet, local_clock, resolve_streams
except ImportError:  # pragma: no cover - depends on local environment
    StreamInfo = None
    StreamInlet = None
    StreamOutlet = None
    local_clock = None
    resolve_streams = None


def default_marker_names(n_markers):
    """Create fallback marker names for unnamed marker streams."""
    return [f"Marker_{i + 1}" for i in range(n_markers)]


def extract_marker_names_from_markers(stream_info):
    """Read marker names from a stream's markers metadata block."""
    names = []
    try:
        markers = stream_info.desc().child("markers")
        marker = markers.child("marker")
        while marker.name():
            label = marker.child_value("label") or marker.child_value("name")
            if label:
                names.append(label)
            marker = marker.next_sibling()
    except Exception:
        return []
    return names


def extract_marker_names(stream_info):
    """Extract marker labels from markers metadata or channel metadata."""
    names = extract_marker_names_from_markers(stream_info)
    if len(names) > 0:
        return names

    names = []
    n_channels = stream_info.channel_count()
    try:
        channels = stream_info.desc().child("channels")
        channel = channels.child("channel")
        while channel.name():
            label = (
                channel.child_value("marker")
                or channel.child_value("label")
                or channel.child_value("name")
            )
            if label:
                names.append(label)
            channel = channel.next_sibling()
    except Exception:
        names = []

    if len(names) == n_channels and n_channels % 4 == 0:
        return names[::4]
    if len(names) == n_channels and n_channels % 3 == 0:
        return names[::3]
    if len(names) > 0:
        return names

    if n_channels % 4 == 0:
        return default_marker_names(n_channels // 4)
    if n_channels % 3 == 0:
        return default_marker_names(n_channels // 3)
    return []


def list_available_streams(wait_time=1.0):
    """Resolve available LSL streams."""
    if resolve_streams is None:
        return []
    return list(resolve_streams(wait_time=wait_time))


def find_matching_stream(streams, stream_name):
    """Select an LSL stream by exact name or return first stream."""
    if stream_name is None:
        return streams[0] if len(streams) > 0 else None

    for stream in streams:
        if stream.name() == stream_name:
            return stream
    return None


def normalize_marker_names(marker_names, expected_count):
    """Normalize raw C3D marker labels to a fixed number of usable names."""
    normalized_names = []
    for index in range(expected_count):
        raw_name = marker_names[index] if index < len(marker_names) else ""
        name = str(raw_name).strip()
        if not name:
            name = f"Marker_{index + 1}"
        normalized_names.append(name)
    return normalized_names


def load_c3d_stream_data(filename):
    """Load point data, marker names, and frame rate from a C3D file."""
    c3d_data = c3d(filename)
    point_data = c3d_data["data"]["points"][0:3, :, :]
    raw_marker_names = list(c3d_data["parameters"]["POINT"]["LABELS"]["value"])
    marker_names = normalize_marker_names(raw_marker_names, point_data.shape[1])
    frame_rate = float(c3d_data["parameters"]["POINT"]["RATE"]["value"][0])
    return point_data, marker_names, frame_rate


def add_marker_metadata(description, marker_names):
    """Append marker and channel metadata to an LSL stream description."""
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
    """Create LSL stream metadata for streaming 3D marker coordinates."""
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


class LSLMarkerNamesViewer:
    """Tkinter utility for inspecting marker names advertised by LSL streams."""

    def __init__(self):
        self.streams = []

        self.root = tk.Tk()
        self.root.title("LSL Marker Names Viewer")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.refresh_btn = tk.Button(self.root, text="Refresh Streams", command=self.refresh_streams)
        self.refresh_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.connect_btn = tk.Button(self.root, text="Show Marker Names", command=self.show_selected_stream_markers)
        self.connect_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.streams_label = tk.Label(self.root, text="Available LSL streams")
        self.streams_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        self.markers_label = tk.Label(self.root, text="Marker names")
        self.markers_label.grid(row=1, column=1, padx=10, pady=(0, 5), sticky="w")

        self.stream_listbox = tk.Listbox(self.root, width=40, height=12, exportselection=False)
        self.stream_listbox.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.marker_listbox = tk.Listbox(self.root, width=40, height=12)
        self.marker_listbox.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")

        self.status_label = tk.Label(self.root, text="Refresh the stream list to begin.", anchor="w", justify="left")
        self.status_label.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        self.refresh_streams()
        self.root.mainloop()

    def set_status(self, message):
        self.status_label.config(text=message)

    def refresh_streams(self):
        self.stream_listbox.delete(0, tk.END)
        self.marker_listbox.delete(0, tk.END)
        self.streams = []

        if resolve_streams is None:
            self.set_status("LSL support is unavailable. Install 'pylsl' first.")
            return

        streams = list_available_streams(wait_time=1.0)
        if len(streams) == 0:
            self.set_status("No LSL streams found.")
            return

        self.streams = list(streams)
        for stream in self.streams:
            stream_label = f"{stream.name()} ({stream.type()}, {stream.channel_count()} channels)"
            self.stream_listbox.insert(tk.END, stream_label)

        self.stream_listbox.selection_set(0)
        self.set_status(f"Found {len(self.streams)} LSL stream(s). Select one to view marker names.")

    def show_selected_stream_markers(self):
        self.marker_listbox.delete(0, tk.END)

        if StreamInlet is None:
            self.set_status("LSL support is unavailable. Install 'pylsl' first.")
            return

        selection = self.stream_listbox.curselection()
        if len(selection) == 0:
            self.set_status("Select an LSL stream first.")
            return

        stream = self.streams[selection[0]]
        inlet = StreamInlet(stream, max_buflen=1, recover=True)
        full_stream_info = inlet.info(timeout=5.0)
        marker_names = extract_marker_names(full_stream_info)
        for marker_name in marker_names:
            self.marker_listbox.insert(tk.END, marker_name)

        if len(marker_names) == 0:
            self.set_status(f"No marker names were found in '{stream.name()}'.")
            return

        self.set_status(f"Showing {len(marker_names)} marker name(s) from '{stream.name()}'.")

    def on_close(self):
        self.root.destroy()


class C3DToLSLStreamer:
    """Tkinter app that replays C3D marker coordinates as an LSL stream."""

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
        if StreamInfo is None or StreamOutlet is None or local_clock is None:
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


def run_marker_names_cli(argv=None):
    """Run command-line marker-name inspection."""
    parser = argparse.ArgumentParser(description="Show marker names from an LSL stream.")
    parser.add_argument("--stream-name", help="Name of the LSL stream to inspect.")
    parser.add_argument(
        "--list-streams",
        action="store_true",
        help="List available streams before selecting one.",
    )
    args = parser.parse_args(argv)

    if resolve_streams is None or StreamInlet is None:
        print("LSL support is unavailable. Install 'pylsl' first.", file=sys.stderr)
        return 1

    streams = list_available_streams(wait_time=1.0)
    if len(streams) == 0:
        print("No LSL streams found.", file=sys.stderr)
        return 1

    if args.list_streams:
        print("Available streams:")
        for stream in streams:
            print(f"- {stream.name()} ({stream.type()}, {stream.channel_count()} channels)")

    stream = find_matching_stream(streams, args.stream_name)
    if stream is None:
        print(f"No LSL stream named '{args.stream_name}' was found.", file=sys.stderr)
        return 1

    inlet = StreamInlet(stream, max_buflen=1, recover=True)
    full_stream_info = inlet.info(timeout=5.0)
    marker_names = extract_marker_names(full_stream_info)

    print(f"Stream: {stream.name()}")
    print(f"Channels: {stream.channel_count()}")
    print("Marker names:")
    for marker_name in marker_names:
        print(marker_name)
    return 0


def main(argv=None):
    """Entrypoint for unified helper modes.

    Modes:
    - viewer
    - streamer
    - cli (default)

    Backward-compatible CLI usage also works:
    python src/LSLHelper.py --list-streams
    """
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) == 0:
        return run_marker_names_cli([])

    mode = argv[0].lower()
    if mode == "viewer":
        LSLMarkerNamesViewer()
        return 0
    if mode == "streamer":
        C3DToLSLStreamer()
        return 0
    if mode == "cli":
        return run_marker_names_cli(argv[1:])

    # Treat unknown first arguments as CLI flags for backward compatibility.
    return run_marker_names_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
