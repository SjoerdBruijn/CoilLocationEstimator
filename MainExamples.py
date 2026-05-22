#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MainExamples.py
===============

Example script for running coil location estimation and animation.

This script demonstrates how to:
- Define reference and experimental C3D files
- Specify marker names for coil, head, and stimulation point
- Create a coil data structure from the reference file
- Compute coil displacement using the experimental file
- Visualize the results with the AnimationApp
- Optionally launch the GUI for interactive use

Usage:
    python MainExamples.py

Requirements:
    - ezc3d
    - matplotlib
    - numpy
    - All project source files in the 'src' directory

Make sure the C3D files (e.g., 'Jen Cal 05.c3d', 'Jen Cal 08.c3d') are present in the working directory.

Author: sjoerdbruijn
Date: 2024-10-14
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ezc3d import c3d
import CoilLocationFcns as clf
from CoilLocationGUI import EstimatorGUI
from AnimationBackend import AnimationApp 

# Reference C3D file and marker names
reffilename = "Jen Cal 05.c3d"
coilmarkernames = ['LHELM', 'RHELM', 'REARHELM1']
stimpointmarkername = ['*6']
headmarkernames = ["LHEAD", "RHEAD", "NASION"]

# Create coil data structure from reference file
coildatastructure = clf.create_coil_data(
    reffilename, coilmarkernames, headmarkernames, stimpointmarkername)

# Experimental C3D file
expfilename = "Jen Cal 08.c3d"

# Add experiment-specific head reference data
coildatastructure = clf.create_headrefdata(expfilename, coildatastructure)
# Compute coil displacement using experimental file
coildisplacement, coildatastructure = clf.get_coil_displacement(
    expfilename, coildatastructure)

# Visualize the results
AnimationApp(coildisplacement)

# Optionally launch the GUI (uncomment to use)
EstimatorGUI()
