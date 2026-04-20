#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from CoilLocationAnimationApp import AnimationApp
import CoilLocationFcns as clf
import numpy as np
import tkinter as tk
from tkinter import filedialog

try:
    from pylsl import StreamInlet, resolve_streams
except ImportError:  # pragma: no cover - depends on local environment
    StreamInlet = None
    resolve_streams = None

# todo; proper behaviour when head tracking window is closed while tracking is active (currently just stops tracking and shows error in status)
# todo; logic of stimpoint for ref in head an coil coordinates does not seem correct yet
class RealtimeGUI:
    def __init__(self):
        self.reffilename = None
        self.coildatastructure = None
        self.inlet = None
        self.stream_info = None
        self.stream_markernames = []
        self.animation_app = None
        self.tracking_active = False
        self.poll_job = None
        self.poll_interval_ms = 5

        self.root = tk.Tk()
        self.root.title("Realtime Coil Data GUI")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.file_btn = tk.Button(self.root, text="Select reference file", command=self.select_ref_file)
        self.file_btn.grid(row=0, column=0, padx=10, pady=10)

        self.file_label = tk.Label(self.root, text="No file selected", width=50, anchor="w")
        self.file_label.grid(row=0, column=1, padx=10, pady=10)

        self.create_coil_btn = tk.Button(self.root, text="Create Coil Data Structure", command=self.create_coildatastructure)
        self.create_coil_btn.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.connect_btn = tk.Button(self.root, text="Connect to LSL", command=self.connect_to_lsl)
        self.connect_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.reference_btn = tk.Button(self.root, text="Reference", command=self.reference_head_markers)
        self.reference_btn.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.track_btn = tk.Button(self.root, text="Run Head Tracking", command=self.run_head_tracking)
        self.track_btn.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.stop_btn = tk.Button(self.root, text="Stop Tracking", command=self.stop_tracking)
        self.stop_btn.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.status_label = tk.Label(self.root, text="Load a reference file to begin.", anchor="w", justify="left")
        self.status_label.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.root.mainloop()

    def set_status(self, message):
        self.status_label.config(text=message)

    def select_ref_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.reffilename = filename
            self.file_label.config(text=filename)
            self.set_status("Reference file selected.")

    def create_coildatastructure(self):
        if self.reffilename is None:
            self.select_ref_file()
        if self.reffilename is None:
            self.set_status("Reference file selection was cancelled.")
            return
        self.coildatastructure = clf.create_coil_data(self.reffilename)
        self.set_status("Coil data structure created from the reference file.")

    def connect_to_lsl(self):
        if StreamInlet is None:
            self.set_status("LSL support is unavailable. Install 'pylsl' first.")
            return

        streams = resolve_streams(wait_time=1.0)
        if len(streams) == 0:
            self.set_status("No LSL streams found.")
            return

        selected_stream = None
        for stream in streams:
            channel_count = stream.channel_count()
            if channel_count % 3 == 0 or channel_count % 4 == 0:
                selected_stream = stream
                break

        if selected_stream is None:
            self.set_status("No compatible LSL marker stream was found.")
            return

        self.stream_info = selected_stream
        self.inlet = StreamInlet(selected_stream, max_buflen=1, recover=True)
        full_stream_info = self.inlet.info(timeout=5.0)
        self.stream_markernames = self._extract_marker_names(full_stream_info)
        self.set_status(f"Connected to LSL stream '{selected_stream.name()}'.")

    def reference_head_markers(self):
        if self.inlet is None:
            self.set_status("Connect to LSL before collecting a live reference.")
            return
        if self.coildatastructure is None:
            self.set_status("Create the coil data structure first.")
            return

        sample, _ = self.inlet.pull_sample(timeout=5.0)
        if sample is None:
            self.set_status("No LSL frame received for reference.")
            return

        markers = self._sample_to_marker_frame(sample)
        coil_names = self.coildatastructure["coilrefdata"]["names"]
        head_names = self.coildatastructure["headrefdata"]["names"]
        stim_names = self.coildatastructure["stimpointrefdata"]["names"]

        _, head_names, _ = clf.select_markers_from_frame(
            markers,
            self.stream_markernames,
            coilmarkernames=coil_names,
            headmarkernames=head_names,
            stimpointmarkername=stim_names,
            master=self.root
        )
        head_indices = clf.marker_indices(self.stream_markernames, head_names)
        self.coildatastructure["headrefdata"]["names"] = head_names
        self.coildatastructure["headrefdata"]["data"] = markers[:, head_indices].T
        self.set_status("Head reference captured from the live stream.")

    def run_head_tracking(self):
        if self.inlet is None:
            self.set_status("Connect to LSL before starting tracking.")
            return
        if self.coildatastructure is None:
            self.set_status("Create the coil data structure first.")
            return
        if self.coildatastructure["headrefdata"]["data"].size == 0:
            self.set_status("Run 'Reference' first to define the live head markers.")
            return
        if self.tracking_active:
            self.set_status("Tracking is already running.")
            return

        sample, _ = self.inlet.pull_sample(timeout=5.0)
        if sample is None:
            self.set_status("No LSL frame received to start tracking.")
            return

        markers = self._sample_to_marker_frame(sample)
        try:
            outdata, self.coildatastructure = clf.get_coil_displacement_from_frame(
                markers, self.stream_markernames, self.coildatastructure)
        except ValueError as exc:
            self.set_status(str(exc))
            return

        if self.animation_app is None:
            self.animation_app = AnimationApp(outdata, master=self.root, auto_mainloop=False, live_mode=True)
        else:
            self.animation_app.append_frame(outdata)

        self.tracking_active = True
        self._schedule_poll()
        self.set_status("Head tracking is running.")

    def stop_tracking(self):
        self.tracking_active = False
        if self.poll_job is not None:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None
        self.set_status("Tracking stopped.")

    def _schedule_poll(self):
        if self.poll_job is not None:
            self.root.after_cancel(self.poll_job)
        self.poll_job = self.root.after(self.poll_interval_ms, self.poll_lsl)

    def poll_lsl(self):
        if not self.tracking_active or self.inlet is None:
            self.poll_job = None
            return

        processed_sample = False
        outdata_batch = []
        while True:
            sample, _ = self.inlet.pull_sample(timeout=0.0)
            if sample is None:
                break
            processed_sample = True
            markers = self._sample_to_marker_frame(sample)
            try:
                outdata, self.coildatastructure = clf.get_coil_displacement_from_frame(
                    markers, self.stream_markernames, self.coildatastructure)
            except ValueError as exc:
                self.stop_tracking()
                self.set_status(str(exc))
                return
            outdata_batch.append(outdata)

        if processed_sample:
            self.animation_app.append_frames(outdata_batch)
            self.set_status("Receiving live LSL data.")
        self._schedule_poll()

    def _sample_to_marker_frame(self, sample):
        sample_array = np.asarray(sample, dtype=float)
        channel_count = sample_array.size
        n_markers = len(self.stream_markernames)

        if channel_count == n_markers * 3:
            return sample_array.reshape(n_markers, 3).T
        if channel_count == n_markers * 4:
            return sample_array.reshape(n_markers, 4)[:, 0:3].T

        if channel_count % 3 == 0:
            n_markers = channel_count // 3
            if len(self.stream_markernames) != n_markers:
                self.stream_markernames = self._default_marker_names(n_markers)
            return sample_array.reshape(n_markers, 3).T

        if channel_count % 4 == 0:
            n_markers = channel_count // 4
            if len(self.stream_markernames) != n_markers:
                self.stream_markernames = self._default_marker_names(n_markers)
            return sample_array.reshape(n_markers, 4)[:, 0:3].T

        raise ValueError("LSL sample size is not compatible with 3D marker coordinates.")

    def _extract_marker_names(self, stream_info):
        n_channels = stream_info.channel_count()
        names = self._extract_marker_names_from_markers(stream_info)
        if len(names) > 0:
            return names

        names = []
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

        if len(names) == 0:
            if n_channels % 4 == 0:
                return self._default_marker_names(n_channels // 4)
            if n_channels % 3 == 0:
                return self._default_marker_names(n_channels // 3)
            return []

        if len(names) == n_channels and n_channels % 4 == 0:
            return names[::4]
        if len(names) == n_channels and n_channels % 3 == 0:
            return names[::3]
        return names

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
        return [f"Marker_{i+1}" for i in range(n_markers)]

    def on_close(self):
        self.stop_tracking()
        self.root.destroy()


if __name__ == "__main__":
    RealtimeGUI()
