#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk

try:
    from pylsl import StreamInlet, resolve_streams
except ImportError:  # pragma: no cover - depends on local environment
    StreamInlet = None
    resolve_streams = None


class LSLMarkerNamesViewer:
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

        streams = resolve_streams(wait_time=1.0)
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

        selection = self.stream_listbox.curselection()
        if len(selection) == 0:
            self.set_status("Select an LSL stream first.")
            return

        stream = self.streams[selection[0]]
        inlet = StreamInlet(stream, max_buflen=1, recover=True)
        full_stream_info = inlet.info(timeout=5.0)
        marker_names = self._extract_marker_names(full_stream_info)
        for marker_name in marker_names:
            self.marker_listbox.insert(tk.END, marker_name)

        if len(marker_names) == 0:
            self.set_status(f"No marker names were found in '{stream.name()}'.")
            return

        self.set_status(f"Showing {len(marker_names)} marker name(s) from '{stream.name()}'.")

    def _extract_marker_names(self, stream_info):
        names = self._extract_marker_names_from_markers(stream_info)
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
            return self._default_marker_names(n_channels // 4)
        if n_channels % 3 == 0:
            return self._default_marker_names(n_channels // 3)
        return []

    def _extract_marker_names_from_markers(self, stream_info):
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

    def _default_marker_names(self, n_markers):
        return [f"Marker_{i + 1}" for i in range(n_markers)]

    def on_close(self):
        self.root.destroy()


if __name__ == "__main__":
    LSLMarkerNamesViewer()
