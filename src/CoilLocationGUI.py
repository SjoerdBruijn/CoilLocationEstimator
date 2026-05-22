#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 14:42:23 2024

@author: sjoerdbruijn
"""

from AnimationBackend import AnimationApp
import CoilLocationFcns as clf
import tkinter as tk
from tkinter import filedialog

class EstimatorGUI:
    def __init__(self):

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
        filename = filedialog.askopenfilename()
        if filename:
            label_widget.config(text=filename)
        return filename

    def select_ref_file(self):
        self.reffilename = self.select_file(self.file1_label)

    def select_exp_file(self):
        self.expfilename = self.select_file(self.file2_label)

    def select_headref_file(self):
        self.headreffilename = self.select_file(self.headref_file_label)
            
    def create_coildatastructure(self):
        if self.reffilename == None:
            self.select_ref_file()
        self.coildatastructure = clf.create_coil_data(self.reffilename)

    def load_coildatastructure(self):
        filename = filedialog.askopenfilename(
            title="Load coil data structure",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        self.coildatastructure = clf.load_coildatastructure(filename)
        self.headstimpoint = None

    def save_coildatastructure(self):
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
        filename = filedialog.askopenfilename(
            title="Load head reference data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        self.coildatastructure = clf.load_headrefdata(filename)
        self.headstimpoint = None

    def save_headrefdata(self):
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
        if self.reffilename == None:
            self.select_ref_file()
        if self.expfilename == None:
            self.select_exp_file()
        self.outdata,self.coildatastructure = clf.get_coil_displacement(self.expfilename, self.coildatastructure)
        self.headstimpoint = self.outdata.get("headstimpoint")
        self.animation_app = AnimationApp(self.outdata, master=self.root, auto_mainloop=False)
        if self.save_results_var.get():
            clf.save_results(self.outdata, self.coildatastructure)

if __name__ == "__main__":
    EstimatorGUI()
