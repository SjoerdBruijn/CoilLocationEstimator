#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from AnimationBackend import AnimationApp
import CoilLocationFcns as clf
import numpy as np
import tkinter as tk
from tkinter import filedialog

try:
    from pylsl import StreamInlet, resolve_streams
except ImportError:  # pragma: no cover - depends on local environment
    StreamInlet = None
    resolve_streams = None

class RealtimeGUI:
    """Tkinter GUI for live coil-location tracking from an LSL marker stream.

    The GUI manages coil/head reference data, connects to a compatible LSL
    marker stream, converts incoming samples into marker frames, computes live
    displacement dictionaries, and feeds those frames into the animation app.
    """

    def __init__(self):
        """Initialize live-tracking state, Tk widgets, and the event loop.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Stores GUI state on the instance and starts the Tkinter main loop.
        """
        self.reffilename = None
        self.headreffilename = None
        self.coildatastructure = None
        self.inlet = None
        self.stream_info = None
        self.stream_markernames = []
        self.animation_app = None
        self.tracking_active = False
        self.poll_job = None
        self.poll_interval_ms = 5
        self.headstimpoint = None

        self.root = tk.Tk()
        self.root.title("Realtime Coil Data GUI")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.file_btn = tk.Button(self.root, text="Select coil ref file", command=self.select_ref_file)
        self.file_btn.grid(row=0, column=0, padx=10, pady=10)

        self.file_label = tk.Label(self.root, text="No file selected", width=50, anchor="w")
        self.file_label.grid(row=0, column=1, padx=10, pady=10)

        self.create_coil_btn = tk.Button(self.root, text="Create Coil Data Structure", command=self.create_coildatastructure)
        self.create_coil_btn.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.load_coil_btn = tk.Button(self.root, text="Load Coil Data Structure", command=self.load_coildatastructure)
        self.load_coil_btn.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.save_coil_btn = tk.Button(self.root, text="Save Coil Data Structure", command=self.save_coildatastructure)
        self.save_coil_btn.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.headref_file_btn = tk.Button(self.root, text="Select head ref file", command=self.select_headref_file)
        self.headref_file_btn.grid(row=3, column=0, padx=10, pady=10)

        self.headref_file_label = tk.Label(self.root, text="No file selected", width=50, anchor="w")
        self.headref_file_label.grid(row=3, column=1, padx=10, pady=10)

        self.reference_btn = tk.Button(self.root, text="Create Reference Data Structure", command=self.reference_head_markers)
        self.reference_btn.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.load_headref_btn = tk.Button(self.root, text="Load Head Reference Data", command=self.load_headrefdata)
        self.load_headref_btn.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

        self.save_headref_btn = tk.Button(self.root, text="Save Head Reference Data", command=self.save_headrefdata)
        self.save_headref_btn.grid(row=5, column=1, padx=10, pady=10, sticky="ew")

        self.connect_btn = tk.Button(self.root, text="Connect to LSL", command=self.connect_to_lsl)
        self.connect_btn.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.track_btn = tk.Button(self.root, text="Live View", command=self.run_head_tracking)
        self.track_btn.grid(row=7, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.stop_btn = tk.Button(self.root, text="Stop Live View", command=self.stop_tracking)
        self.stop_btn.grid(row=8, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.status_label = tk.Label(self.root, text="Load a reference file to begin.", anchor="w", justify="left")
        self.status_label.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.root.mainloop()

    def set_status(self, message):
        """Display a status message in the realtime GUI.

        Parameters
        ----------
        message : str
            Text describing the latest file, LSL, or tracking state.

        Returns
        -------
        None.
            Updates only the status label text.
        """
        self.status_label.config(text=message)

    def select_ref_file(self):
        """Select the coil reference C3D file used to build coil data.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.reffilename``, the reference label, and the status
            label when a file is selected.
        """
        filename = filedialog.askopenfilename()
        if filename:
            self.reffilename = filename
            self.file_label.config(text=filename)
            self.set_status("Reference file selected.")

    def select_headref_file(self):
        """Select the head reference C3D file used for reference data.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.headreffilename``, the head reference label, and the
            status label when a file is selected.
        """
        filename = filedialog.askopenfilename()
        if filename:
            self.headreffilename = filename
            self.headref_file_label.config(text=filename)
            self.set_status("Head reference file selected.")

    def create_coildatastructure(self):
        """Create coil reference data from the selected coil reference file.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.coildatastructure`` with coil marker and stimulation
            reference data, clears cached head stimulation point state, and
            reports success or cancellation in the status label.
        """
        if self.reffilename is None:
            self.select_ref_file()
        if self.reffilename is None:
            self.set_status("Reference file selection was cancelled.")
            return
        self.coildatastructure = clf.create_coil_data(self.reffilename)
        self.headstimpoint = None
        self.set_status("Coil data structure created from the reference file.")

    def load_coildatastructure(self):
        """Load saved coil reference data from JSON.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Replaces ``self.coildatastructure`` with loaded coil reference
            fields and clears cached head stimulation point state.
        """
        filename = filedialog.askopenfilename(
            title="Load coil data structure",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            self.set_status("Coil data structure loading was cancelled.")
            return
        self.coildatastructure = clf.load_coildatastructure(filename)
        self.headstimpoint = None
        self.set_status("Coil data structure loaded. Head reference data was left empty.")

    def save_coildatastructure(self):
        """Save the current coil reference data to JSON.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Writes a sanitized coil data structure when data and a destination
            path are available; otherwise only updates GUI status.
        """
        if self.coildatastructure is None:
            self.set_status("Create or load the coil data structure first.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save coil data structure",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            self.set_status("Coil data structure saving was cancelled.")
            return
        clf.save_coildatastructure(self.coildatastructure, filename)
        self.set_status("Coil data structure saved without head reference data.")

    def load_headrefdata(self):
        """Load saved head reference data from JSON.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Replaces ``self.coildatastructure`` with loaded head reference data
            and clears cached head stimulation point state.
        """
        filename = filedialog.askopenfilename(
            title="Load head reference data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            self.set_status("Head reference data loading was cancelled.")
            return
        self.coildatastructure = clf.load_headrefdata(filename)
        self.headstimpoint = None
        self.set_status("Head reference data loaded, including saved head stimulation point data when available.")

    def save_headrefdata(self):
        """Save head reference fields from the current data dictionary.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Writes head reference markers and head stimulation point reference
            data to JSON when a data structure and destination are available.
        """
        if self.coildatastructure is None:
            self.set_status("Create or load the coil data structure first.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save head reference data",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            self.set_status("Head reference data saving was cancelled.")
            return
        clf.save_headrefdata(self.coildatastructure, filename)
        self.set_status("Head reference data saved.")

    def connect_to_lsl(self):
        """Connect to the first compatible live LSL marker stream.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.stream_info``, ``self.inlet``, and
            ``self.stream_markernames`` when a compatible stream is found.
        """
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
        """Create head reference data from the selected head reference file.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.coildatastructure`` with head marker reference data
            and head stimulation point reference data, or reports an error in
            the status label.
        """
        if self.coildatastructure is None:
            self.set_status("Create the coil data structure first.")
            return
        if self.headreffilename is None:
            self.select_headref_file()
        if self.headreffilename is None:
            self.set_status("Head reference file selection was cancelled.")
            return

        try:
            self.coildatastructure = clf.create_headrefdata(
                self.headreffilename,
                self.coildatastructure)
        except (IndexError, ValueError) as exc:
            self.set_status(str(exc))
            return
        self.headstimpoint = None
        self.set_status("Head reference data structure created from the head reference file.")

    def run_head_tracking(self):
        """Start live tracking and initialize or resume the animation app.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Pulls an initial LSL sample, converts it to marker coordinates,
            computes a displacement frame, starts polling, and sends data to
            the animation app.
        """
        if self.inlet is None:
            self.set_status("Connect to LSL before starting live view.")
            return
        if self.coildatastructure is None:
            self.set_status("Create the coil data structure first.")
            return
        if self.coildatastructure["headrefdata"]["data"].size == 0:
            self.set_status("Create reference data structure first.")
            return
        if "headstimpointrefdata" not in self.coildatastructure:
            self.set_status("Create or load head stimulation point reference data first.")
            return
        if self.tracking_active:
            self.set_status("Live view is already running.")
            return

        sample, _ = self.inlet.pull_sample(timeout=5.0)
        if sample is None:
            self.set_status("No LSL frame received to start live view.")
            return

        try:
            outdata = self._process_lsl_sample(sample)
        except ValueError as exc:
            self.set_status(str(exc))
            return

        if self.animation_app is None:
            self.animation_app = AnimationApp(
                outdata,
                master=self.root,
                auto_mainloop=False,
                live_mode=True,
                on_close_callback=self.on_animation_closed,
            )
        else:
            self.animation_app.append_frame(outdata)
            self.animation_app.play()

        self.tracking_active = True
        self._schedule_poll()
        self.set_status("Live view is running.")

    def stop_tracking(self):
        """Stop live tracking and cancel any pending LSL poll callback.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Sets ``self.tracking_active`` false, clears ``self.poll_job``, and
            updates the status label.
        """
        self.tracking_active = False
        if self.poll_job is not None:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None
        self.set_status("Live view stopped.")

    def on_animation_closed(self):
        """Handle manual closing of the animation window.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Stops live tracking and clears the animation app reference so live
            view can be restarted later.
        """
        self.stop_tracking()
        self.animation_app = None

    def _schedule_poll(self):
        """Schedule the next non-blocking LSL polling callback.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Replaces any previous scheduled callback with a new Tk ``after``
            job stored in ``self.poll_job``.
        """
        if self.poll_job is not None:
            self.root.after_cancel(self.poll_job)
        self.poll_job = self.root.after(self.poll_interval_ms, self.poll_lsl)

    def poll_lsl(self):
        """Drain available LSL samples and append them to the animation.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Converts every available sample into marker frames, updates the coil
            data structure through displacement calculations, appends frames to
            the animation app, and reschedules polling while tracking remains
            active.
        """
        if not self.tracking_active or self.inlet is None:
            self.poll_job = None
            return
        if self.animation_app is None:
            self.stop_tracking()
            return

        processed_sample = False
        outdata_batch = []
        while True:
            sample, _ = self.inlet.pull_sample(timeout=0.0)
            if sample is None:
                break
            processed_sample = True
            try:
                outdata = self._process_lsl_sample(sample)
            except ValueError as exc:
                self.stop_tracking()
                self.set_status(str(exc))
                return
            outdata_batch.append(outdata)

        if processed_sample and self.animation_app is not None:
            self.animation_app.append_frames(outdata_batch)
            self.set_status("Receiving live LSL data.")
        if self.tracking_active:
            self._schedule_poll()

    def _process_lsl_sample(self, sample):
        """Convert one LSL sample into displacement output data.

        Parameters
        ----------
        sample : sequence of float
            Flat LSL channel data containing marker coordinates.

        Returns
        -------
        dict
            Single-frame coil displacement dictionary returned by
            ``clf.get_coil_displacement_from_frame``.

        Raises
        ------
        ValueError
            Propagated when sample shape or required marker data are invalid.
        """
        markers = self._sample_to_marker_frame(sample)
        outdata, self.coildatastructure = clf.get_coil_displacement_from_frame(
            markers, self.stream_markernames, self.coildatastructure)
        self.headstimpoint = outdata.get("headstimpoint")
        return outdata

    def _sample_to_marker_frame(self, sample):
        """Convert one flat LSL sample into a ``3 x n_markers`` array.

        Parameters
        ----------
        sample : sequence of float
            Flat LSL channel data containing either XYZ triples or XYZW groups
            for each marker.

        Returns
        -------
        numpy.ndarray
            Marker coordinate matrix with rows ``X, Y, Z`` and one column per
            marker. The method may also refresh default marker names when the
            channel count implies a different marker count.
        """
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
        """Extract marker names from LSL stream metadata.

        Parameters
        ----------
        stream_info : pylsl.StreamInfo
            Full LSL stream metadata returned by an inlet.

        Returns
        -------
        list of str
            Marker labels from the ``markers`` block, channel metadata, or
            generated fallback labels inferred from the channel count.
        """
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
        """Read marker labels from the LSL metadata ``markers`` block.

        Parameters
        ----------
        stream_info : pylsl.StreamInfo
            Full stream metadata that may contain a ``markers`` XML node.

        Returns
        -------
        list of str
            Labels found in marker metadata, or an empty list when unavailable.
        """
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
        """Create fallback marker labels for streams without metadata.

        Parameters
        ----------
        n_markers : int
            Number of marker names to generate.

        Returns
        -------
        list of str
            Labels in the form ``Marker_1``, ``Marker_2``, and so on.
        """
        return [f"Marker_{i+1}" for i in range(n_markers)]

    def on_close(self):
        """Close the realtime GUI and any active animation cleanly.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Stops tracking, closes the animation app when present, clears its
            reference, and destroys the Tk root window.
        """
        self.stop_tracking()
        if self.animation_app is not None:
            self.animation_app.on_close()
            self.animation_app = None
        self.root.destroy()


if __name__ == "__main__":
    RealtimeGUI()
