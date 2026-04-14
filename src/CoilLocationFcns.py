#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 14:37:40 2024

@author: sjoerdbruijn
"""
from ezc3d import c3d
from MarkerSelectionGui import MarkerSelector
import numpy as np

def select_markers(filename, coilmarkernames=[], headmarkernames=[], stimpointmarkername=[]):
    """
    Launches a GUI to select coil, head, and stimulation point marker names from a C3D file.
    
    Parameters:
        filename (str): Path to the C3D file.
        coilmarkernames (list): List of coil marker names (optional).
        headmarkernames (list): List of head marker names (optional).
        stimpointmarkername (list): List of stimulation point marker names (optional).
    
    Returns:
        tuple: (coilmarkernames, headmarkernames, stimpointmarkername) as selected by the user.
    """
    point_data, markernames, firstind = getkindata(filename)
    markerselector = MarkerSelector(point_data[:,:,firstind], markernames,
                                    coilmarkernames,
                                    headmarkernames,
                                    stimpointmarkername)
    coilmarkernames, headmarkernames, stimpointmarkername = markerselector.get_marker_names()
    return coilmarkernames, headmarkernames, stimpointmarkername
    
def marker_indices(markernames, names_to_find):
    indices = []
    for name in names_to_find:
        found = False
        for i, m in enumerate(markernames):
            if m.split(":")[-1].strip().upper() == name.strip().upper():
                indices.append(i)
                found = True
                break
        if not found:
            print(f"'{name}' not found in the list.")
    return indices

def extract_marker_data(point_data, firstind, indices):
    return point_data.transpose(2, 0, 1)[firstind, 0:3, indices].T

def getkindata(filename, selectedmarkernames=None):
    """
    Loads kinematic data and marker labels from a C3D file and finds the first frame where all selected markers are visible.

    Parameters:
        filename (str): Path to the C3D file.
        selectedmarkernames (list or None): List of marker names to check for visibility. If None, uses all markers.

    Returns:
        tuple: (point_data, markernames, firstind)
            point_data (np.ndarray): The marker data array.
            markernames (list): List of all marker names in the file.
            firstind (int): Index of the first frame where all selected markers are visible.
    """
    c = c3d(filename)
    point_data = c['data']['points']
    markernames = c['parameters']['POINT']['LABELS']['value']
    if selectedmarkernames is None: 
        selectedmarkernames = markernames 
    index = marker_indices(markernames, selectedmarkernames)
    # find the first sample where none of the markers is NaN
    try:
        firstind = np.where(
            ~np.isnan(np.sum(point_data[0, index, :], axis=0)))[0][0]
    except:
        firstind =np.argmax(np.sum(~np.isnan(point_data[0, index, :]),axis=0))
        
    return point_data, markernames, firstind


def create_coil_data(filename, coilmarkernames=None, headmarkernames=None, stimpointmarkername=None):
    """
    Creates a coil data structure from a C3D file, containing coil, head, and stimulation point marker data.

    Parameters:
        filename (str): Path to the C3D file.
        coilmarkernames (list): List of coil marker names.
        headmarkernames (list): List of head marker names.
        stimpointmarkername (list): List of stimulation point marker names.

    Returns:
        dict: Coil data structure with marker names and corresponding data arrays.
    """
    if coilmarkernames is None:
        coilmarkernames = []
    if headmarkernames is None:
        headmarkernames = []
    if stimpointmarkername is None:
        stimpointmarkername = []
    # find first sample where all markers visible
    # make a list of all markers relevant, and find them in the data
    if (coilmarkernames == [] or
        headmarkernames == [] or
        stimpointmarkername == []):
        coilmarkernames, headmarkernames, stimpointmarkername = select_markers(filename, coilmarkernames, headmarkernames, stimpointmarkername)
    allmarkernames = headmarkernames + coilmarkernames + stimpointmarkername
    point_data, markernames, firstind = getkindata(filename, allmarkernames)
    # create coil data structure
    coildatastructure = {
        "coilrefdata": {"names": coilmarkernames},
        "headrefdata": {"names": headmarkernames},
        "stimpointrefdata": {"names": stimpointmarkername}
    }

    # Add and update the 'data' key in each inner dictionary
    for key in coildatastructure:
        index = marker_indices(markernames, coildatastructure[key]["names"])
        coildatastructure[key]["data"] = extract_marker_data(point_data, firstind, index)
    return coildatastructure


def get_coil_displacement(expfilename, coildatastructure):
    """
    Computes coil displacement and updates the coil data structure using experimental data.

    Parameters:
        expfilename (str): Path to the experimental C3D file.
        coildatastructure (dict): Coil data structure with reference data.

    Returns:
        tuple: (coildisplacement, coildatastructure)
            coildisplacement (dict): Displacement data for head and coil markers, and calculated stimulation points.
            coildatastructure (dict): Updated coil data structure.
    """
    
    if coildatastructure["headrefdata"]["names"]==[]: #TODO
        _, coildatastructure["headrefdata"]["names"], _ = select_markers(expfilename, coildatastructure["coilrefdata"]["names"],coildatastructure["headrefdata"]["names"],coildatastructure["stimpointrefdata"]["names"])

        
    allmarkernames = coildatastructure["headrefdata"]["names"] + \
        coildatastructure["coilrefdata"]["names"] + \
        coildatastructure["stimpointrefdata"]["names"]
    point_data, markernames, firstind = getkindata(expfilename, allmarkernames)

    # TODO; this is probably empty, in which case use first sample all visible! see also line ??
    if coildatastructure["headrefdata"]['data'].size == 0:
        # TODO, or when using current as ref..
        index = marker_indices(markernames, coildatastructure["headrefdata"]["names"])
        coildatastructure["headrefdata"]["data"] = extract_marker_data(point_data, firstind, index)
    else:
        print('using previously calculated head data as reference')
    headrefdata = coildatastructure["headrefdata"]["data"]
    coilrefdata = coildatastructure["coilrefdata"]["data"]
    point = coildatastructure["stimpointrefdata"]["data"]

    # get exp data
    coildisplacement = dict()
    for key in ["headrefdata", "coilrefdata"]:
        index = marker_indices(markernames, coildatastructure[key]["names"])
        coildisplacement[key] = point_data.transpose(2, 0, 1)[:, 0:3, index]

    # calculate stim point during exp
    coildisplacement['coilR'], coildisplacement["coilstimpoint"],_ ,_= rigidbodytransform(
        coilrefdata, coildisplacement["coilrefdata"], point)
    coildisplacement['headR'], coildisplacement["headstimpoint"],_,_ = rigidbodytransform(
        headrefdata, coildisplacement["headrefdata"], coildisplacement["coilstimpoint"][firstind])

    return coildisplacement, coildatastructure


def rigidbodytransform(A, B, virt_marker=None):
    """
    Computes the rotation matrices that align A to B for each time sample,
    handling cases where B contains NaN values, and calculates the position of the virtual marker in B.

    Parameters:
        A (numpy.ndarray): An m x 3 x n array of points.
        B (numpy.ndarray): An m x 3 x n array of points.
        virt_marker (numpy.ndarray): A 1 x 3 array representing the position of the virtual marker in the coordinate system of A.

    Returns:
        tuple: (R, virt_marker_in_B, t, rmsd)
            R (numpy.ndarray): An m x 3 x 3 array of rotation matrices for each time sample.
            virt_marker_in_B (numpy.ndarray): An m x 3 array representing the position of the virtual marker in the coordinate system of B for each time sample.
            t (numpy.ndarray): Translation vectors for each time sample.
            rmsd (numpy.ndarray): Root mean square deviation for each time sample.
    """
    if virt_marker is None:
       virt_marker= np.full((1,3, 1), np.nan)
    
 
    # Ensure A and B are numpy arrays
    A = np.asarray(A)
    B = np.asarray(B)
    virt_marker = np.asarray(virt_marker)  # Ensure virt_marker is a 1x3 array

    # Number of time samples
    m, _, n = B.shape

    # handle the case where A is only present for one sample.
    if A.shape[0] == 1 or A.ndim == 2:
        A = np.tile(A, (m, 1, 1))
        
    if virt_marker.shape[0] == 1 or virt_marker.ndim == 2: 
        virt_marker = np.tile(virt_marker, (m, 1, 1))

    assert A.shape == B.shape, "Matrix dimensions must match, and do not for some reason"

    # Initialize outputs
    R = np.full((m, 3, 3), np.nan)  # m x 3 x 3 identity matrices
    virt_marker_in_B = np.full(
        (m, 3, virt_marker.shape[2]), np.nan)  # Initialize with NaNs
    t = np.full((m, 3), np.nan)  # m x 3 x 3 identity matrices
    rmsd = np.full((m), np.nan)  # m 
    

    # Create a mask for valid (non-NaN) markers
    valid_mask = ~np.isnan(B).any(axis=1)  # Shape: m x n

    # Count valid markers for each time sample
    n_valid = np.sum(valid_mask, axis=1)  # Shape: m
    # Valid samples (with at least 3 valid markers)
    valid_samples = n_valid >= 3
    # Process only valid samples
    if np.any(valid_samples):
        A_valid = A[valid_samples]  # Extract valid samples
        B_valid = B[valid_samples]
        virt_marker_valid = virt_marker[valid_samples]

        valid_mask_valid = valid_mask[valid_samples]
        # Shape: valid_samples x 1 x 1
        n_valid_valid = n_valid[valid_samples].reshape(-1, 1)

        # Apply the mask to A and B, setting invalid markers to zero
        A_masked = np.where(valid_mask_valid[:, np.newaxis, :], A_valid, 0)
        B_masked = np.where(valid_mask_valid[:, np.newaxis, :], B_valid, 0)

        # Compute centroids for valid points
        centroid_A = np.sum(A_masked, axis=2) / n_valid_valid
        centroid_B = np.sum(B_masked, axis=2) / n_valid_valid
        # Optimal translation
        t[valid_samples] = centroid_B - centroid_A  # mx1x3

        # Center the points
        # Shape: valid_samples x 3 x n
        AA = A_masked - centroid_A[:, :, np.newaxis]
        BB = B_masked - centroid_B[:, :, np.newaxis]
        
        # set the zeros back to zero, so that doesnt influence covariance matrix calculation
        AA = np.where(valid_mask_valid[:, np.newaxis, :],AA,0)
        BB = np.where(valid_mask_valid[:, np.newaxis, :],BB,0)
   

        # Compute covariance matrices for valid points
        H = np.matmul(AA, BB.transpose(0, 2, 1))

        # Perform Singular Value Decomposition (SVD)
        U, S, Vt = np.linalg.svd(H)

        # Compute rotation matrices
        R_valid = np.matmul(Vt.transpose(0, 2, 1), U.transpose(0, 2, 1))

        # Handle reflections (where the determinant is negative)
        det_R_valid = np.linalg.det(R_valid)
        Vt[det_R_valid < 0, 2, :] *= -1
        R_valid = np.matmul(Vt.transpose(0, 2, 1), U.transpose(0, 2, 1))

        # Place computed rotation matrices back into the full rotation matrix array
        R[valid_samples] = R_valid

        # Apply the rotation matrices to the virtual marker
        virt_marker_centered = virt_marker_valid - \
            centroid_A[:, :, np.newaxis]  # Shape: valid_samples x 3
        virt_marker_in_B_valid = np.matmul(
            R_valid, virt_marker_centered) + centroid_B[:, :, np.newaxis]


        # Place computed virtual marker positions back into the full output array
        virt_marker_in_B[valid_samples] = virt_marker_in_B_valid
        
        # RMSD
        rmsd[valid_samples] = np.sqrt(np.sum(np.sum(np.square(np.matmul(R_valid,AA) - BB),axis=1),axis=1))


    return R, virt_marker_in_B, t , rmsd
