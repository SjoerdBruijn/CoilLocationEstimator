#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 14:42:23 2024

@author: sjoerdbruijn
"""

from AnimationBackend import AnimationApp
import CoilLocationFcns as clf
import tkinter as tk
from tkinter import filedialog, messagebox

class EstimatorGUI:
    """Tkinter GUI for offline coil-location estimation from C3D files.

    The GUI stores selected file paths, builds or loads the coil/head reference
    data dictionaries, computes coil displacement for an experimental file, and
    launches an animation viewer for the resulting displacement arrays.
    """

    def __init__(self):
        """Initialize the offline GUI, internal data fields, and Tk widgets.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            The constructor starts the Tkinter main loop and keeps state on the
            instance while the user selects files and runs computations.
        """

        self.reffilename = None
        self.headreffilename = None
        self.expfilename = None
        self.coildatastructure = None
        self.outdata = None 
        self.headstimpoint = None
        self.animation_app = None
        self.save_results = False        

        # Initialize the Tkinter window
        self.root = tk.Tk()
        self.root.title("Coil Data GUI")
        
        # File selection section
        self.file1_btn = tk.Button(self.root, text="Select coil ref file", command=self.select_ref_file)
        self.file1_btn.grid(row=0, column=0, padx=10, pady=10)
        
        self.file1_label = tk.Label(self.root, text="No file selected", width=50, anchor="w")
        self.file1_label.grid(row=0, column=1, padx=10, pady=10)
        
        # Functionality section
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

        self.file2_btn = tk.Button(self.root, text="Select experimental file", command=self.select_exp_file)
        self.file2_btn.grid(row=6, column=0, padx=10, pady=10)

        self.file2_label = tk.Label(self.root, text="No file selected", width=50, anchor="w")
        self.file2_label.grid(row=6, column=1, padx=10, pady=10)

        self.calculate_btn = tk.Button(self.root, text="Show Data", command=self.calculate_coil_displacement)
        self.calculate_btn.grid(row=7, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Save results checkbox
        self.save_results_var = tk.BooleanVar()
        self.save_results_checkbox = tk.Checkbutton(self.root, text="Save Results", variable=self.save_results_var)
        self.save_results_checkbox.grid(row=8, column=0, columnspan=2, padx=10, pady=10)
        
        # Run the Tkinter event loop
        self.root.mainloop()
        
    def select_file(self, label_widget):
        """Ask the user for a file path and mirror it into a label widget.

        Parameters
        ----------
        label_widget : tkinter.Label
            Label whose text is replaced with the selected file path.

        Returns
        -------
        str or None
            The selected filename, or ``None`` when the dialog is cancelled.
        """
        filename = filedialog.askopenfilename()
        if filename:
            label_widget.config(text=filename)
        return filename

    def select_ref_file(self):
        """Select the coil reference C3D file and store its path.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.reffilename`` and the coil reference file label.
        """
        self.reffilename = self.select_file(self.file1_label)

    def select_exp_file(self):
        """Select the experimental C3D file and store its path.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.expfilename`` and the experimental file label.
        """
        self.expfilename = self.select_file(self.file2_label)

    def select_headref_file(self):
        """Select the head reference C3D file and store its path.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.headreffilename`` and the head reference file label.
        """
        self.headreffilename = self.select_file(self.headref_file_label)
            
    def create_coildatastructure(self):
        """Create the coil data dictionary from the selected reference file.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.coildatastructure`` with marker selections, coil
            reference data, and coil stimulation point reference data.
        """
        if self.reffilename == None:
            self.select_ref_file()
        self.coildatastructure = clf.create_coil_data(self.reffilename)

    def load_coildatastructure(self):
        """Load a saved coil data dictionary from JSON.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Replaces ``self.coildatastructure`` with the loaded dictionary and
            clears cached head stimulation point state.
        """
        filename = filedialog.askopenfilename(
            title="Load coil data structure",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        self.coildatastructure = clf.load_coildatastructure(filename)
        self.headstimpoint = None

    def save_coildatastructure(self):
        """Save the current coil data dictionary to JSON.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Writes a sanitized copy of ``self.coildatastructure`` when data and
            an output path are available.
        """
        if self.coildatastructure is None:
            return
        filename = filedialog.asksaveasfilename(
            title="Save coil data structure",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        clf.save_coildatastructure(self.coildatastructure, filename)

    def load_headrefdata(self):
        """Load a saved head reference dictionary from JSON.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Replaces ``self.coildatastructure`` with the loaded reference data
            and clears cached head stimulation point state.
        """
        filename = filedialog.askopenfilename(
            title="Load head reference data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        self.coildatastructure = clf.load_headrefdata(filename)
        self.headstimpoint = None

    def save_headrefdata(self):
        """Save head reference fields from the current data dictionary.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Writes head marker reference data and head stimulation point
            reference data to JSON when available.
        """
        if self.coildatastructure is None:
            return
        filename = filedialog.asksaveasfilename(
            title="Save head reference data",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        clf.save_headrefdata(self.coildatastructure, filename)

    def reference_head_markers(self):
        """Create head reference data from the selected head reference file.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Ensures coil data exists, then updates ``self.coildatastructure``
            with ``headrefdata`` and ``headstimpointrefdata``.
        """
        if self.coildatastructure is None:
            if self.reffilename == None:
                self.select_ref_file()
            if self.reffilename == None:
                return
            self.coildatastructure = clf.create_coil_data(self.reffilename)
        if self.headreffilename == None:
            self.select_headref_file()
        if self.headreffilename == None:
            return
        self.coildatastructure = clf.create_headrefdata(self.headreffilename, self.coildatastructure)
        self.headstimpoint = None

    def calculate_coil_displacement(self):
        """Compute displacement data for the selected experimental file.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
            Updates ``self.outdata`` and ``self.coildatastructure``, stores the
            current head stimulation point array, launches the animation app,
            and optionally saves results.
        """
        if self.reffilename == None:
            self.select_ref_file()
        if self.expfilename == None:
            self.select_exp_file()
        if self.coildatastructure is None:
            messagebox.showerror("Cannot show data", "Create or load the coil data structure first.")
            return
        try:
            self.outdata,self.coildatastructure = clf.get_coil_displacement(self.expfilename, self.coildatastructure)
        except ValueError as exc:
            messagebox.showerror("Cannot show data", str(exc))
            return
        self.headstimpoint = self.outdata.get("headstimpoint")
        self.animation_app = AnimationApp(self.outdata, master=self.root, auto_mainloop=False)
        if self.save_results_var.get():
            clf.save_results(self.outdata, self.coildatastructure)

if __name__ == "__main__":
    EstimatorGUI()
