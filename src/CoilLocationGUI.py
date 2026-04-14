#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 14:42:23 2024

@author: sjoerdbruijn
"""

from CoilLocationAnimationApp import AnimationApp
import CoilLocationFcns as clf
import tkinter as tk
from tkinter import filedialog

class EstimatorGUI:
    def __init__(self):

        self.reffilename = None
        self.expfilename = None
        self.coildatastructure = None
        self.outdata = None 
        self.save_results = False        

        # Initialize the Tkinter window
        self.root = tk.Tk()
        self.root.title("Coil Data GUI")
        
        # File selection section
        self.file1_btn = tk.Button(self.root, text="Select reference file", command=self.select_ref_file)
        self.file1_btn.grid(row=0, column=0, padx=10, pady=10)
        
        self.file1_label = tk.Label(self.root, text="No file selected", width=50, anchor="w")
        self.file1_label.grid(row=0, column=1, padx=10, pady=10)
        
        self.file2_btn = tk.Button(self.root, text="Select experimental file", command=self.select_exp_file)
        self.file2_btn.grid(row=1, column=0, padx=10, pady=10)
        
        self.file2_label = tk.Label(self.root, text="No file selected", width=50, anchor="w")
        self.file2_label.grid(row=1, column=1, padx=10, pady=10)
        
        # Functionality section
        self.create_coil_btn = tk.Button(self.root, text="Create Coil Data Structure", command=self.create_coildatastructure)
        self.create_coil_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        
        self.calculate_btn = tk.Button(self.root, text="Calculate Experimental File", command=self.calculate_coil_displacement)
        self.calculate_btn.grid(row=3, column=0, columnspan=2, padx=10, pady=10)
        
        # Save results checkbox
        self.save_results_var = tk.BooleanVar()
        self.save_results_checkbox = tk.Checkbutton(self.root, text="Save Results", variable=self.save_results_var)
        self.save_results_checkbox.grid(row=4, column=0, columnspan=2, padx=10, pady=10)
        
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
            
    def create_coildatastructure(self):
        if self.reffilename == None:
            self.select_ref_file()
        self.coildatastructure = clf.create_coil_data(self.reffilename)

    def calculate_coil_displacement(self):
        if self.reffilename == None:
            self.select_ref_file()
        if self.expfilename == None:
            self.select_exp_file()
        self.outdata,self.coildatastructure = clf.get_coil_displacement(self.expfilename, self.coildatastructure)
        AnimationApp(self.outdata)
        if self.save_results_var.get():
            clf.save_results(self.outdata, self.coildatastructure)

if __name__ == "__main__":
    EstimatorGUI()






