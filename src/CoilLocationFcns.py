#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 14:37:40 2024

@author: sjoerdbruijn
"""
from ezc3d import c3d
from MarkerSelectionGui import MarkerSelector
import json
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


def select_markers_from_frame(markers, markernames, coilmarkernames=None, headmarkernames=None,
                              stimpointmarkername=None, master=None):
    """
    Launches the marker selector on an in-memory frame instead of a C3D file.
    """
    if coilmarkernames is None:
        coilmarkernames = []
    if headmarkernames is None:
        headmarkernames = []
    if stimpointmarkername is None:
        stimpointmarkername = []
    markerselector = MarkerSelector(markers, markernames,
                                    coilmarkernames,
                                    headmarkernames,
                                    stimpointmarkername,
                                    master=master)
    return markerselector.get_marker_names()
    
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
        "coilstimpointrefdata": {"names": stimpointmarkername}
    }

    # Add and update the 'data' key in each inner dictionary
    for key in coildatastructure:
        index = marker_indices(markernames, coildatastructure[key]["names"])
        coildatastructure[key]["data"] = extract_marker_data(point_data, firstind, index)
    return coildatastructure


def create_coil_data_from_frame(markers, markernames, coilmarkernames=None, headmarkernames=None,
                                stimpointmarkername=None, master=None):
    """
    Creates a coil data structure from a single marker frame.
    """
    if coilmarkernames is None:
        coilmarkernames = []
    if headmarkernames is None:
        headmarkernames = []
    if stimpointmarkername is None:
        stimpointmarkername = []

    if (coilmarkernames == [] or
        headmarkernames == [] or
        stimpointmarkername == []):
        coilmarkernames, headmarkernames, stimpointmarkername = select_markers_from_frame(
            markers, markernames, coilmarkernames, headmarkernames, stimpointmarkername, master=master)

    coildatastructure = {
        "coilrefdata": {"names": coilmarkernames},
        "headrefdata": {"names": headmarkernames},
        "coilstimpointrefdata": {"names": stimpointmarkername}
    }
    marker_frame = np.asarray(markers)
    if marker_frame.shape[0] != 3:
        raise ValueError("Expected markers with shape 3 x n_markers.")

    for key in coildatastructure:
        index = marker_indices(markernames, coildatastructure[key]["names"])
        coildatastructure[key]["data"] = marker_frame[:, index].T
    return coildatastructure


def create_headrefdata(filename, coildatastructure, sample_number=None):
    """
    Adds experiment-specific head reference data to an existing coil data structure.

    Parameters:
        filename (str): Path to the experimental C3D file.
        coildatastructure (dict): Coil data structure created by create_coil_data.
        sample_number (int or None): Zero-based sample to use as head reference.
            If None, uses the first sample where all required markers are visible.

    Returns:
        dict: The updated coil data structure.
    """

    if coildatastructure["headrefdata"]["names"] == []:
        _, coildatastructure["headrefdata"]["names"], _ = select_markers(
            filename,
            coildatastructure["coilrefdata"]["names"],
            coildatastructure["headrefdata"]["names"],
            coildatastructure["coilstimpointrefdata"]["names"])

    required_markernames = (
        coildatastructure["headrefdata"]["names"] +
        coildatastructure["coilrefdata"]["names"]
    )
    point_data, markernames, firstind = getkindata(filename, required_markernames)

    if sample_number is None:
        sample_number = firstind

    n_samples = point_data.shape[2]
    if sample_number < 0 or sample_number >= n_samples:
        raise IndexError(
            f"sample_number {sample_number} is outside the available range 0-{n_samples - 1}.")

    headindex = marker_indices(markernames, coildatastructure["headrefdata"]["names"])
    coilindex = marker_indices(markernames, coildatastructure["coilrefdata"]["names"])

    if len(headindex) != len(coildatastructure["headrefdata"]["names"]):
        raise ValueError("Not all head markers were found in the experimental data.")
    if len(coilindex) != len(coildatastructure["coilrefdata"]["names"]):
        raise ValueError("Not all coil markers were found in the experimental data.")

    coildatastructure["headrefdata"]["data"] = extract_marker_data(
        point_data, sample_number, headindex)

    experimental_headdata = point_data.transpose(2, 0, 1)[:, 0:3, headindex]
    experimental_coildata = point_data.transpose(2, 0, 1)[:, 0:3, coilindex]

    _, coilstimpoint_at_reference, _, _ = rigidbodytransform(
        coildatastructure["coilrefdata"]["data"],
        experimental_coildata[sample_number:sample_number + 1],
        coildatastructure["coilstimpointrefdata"]["data"])

    coildatastructure["headstimpointrefdata"] = coilstimpoint_at_reference
    

    return coildatastructure


def create_headrefdata_from_frame(markers, markernames, coildatastructure, master=None):
    """
    Adds head reference data to an existing coil data structure from one marker frame.
    """
    marker_frame = np.asarray(markers)
    if marker_frame.shape[0] != 3:
        raise ValueError("Expected markers with shape 3 x n_markers.")

    if coildatastructure["headrefdata"]["names"] == []:
        _, coildatastructure["headrefdata"]["names"], _ = select_markers_from_frame(
            marker_frame,
            markernames,
            coildatastructure["coilrefdata"]["names"],
            coildatastructure["headrefdata"]["names"],
            coildatastructure["coilstimpointrefdata"]["names"],
            master=master)

    headindex = marker_indices(markernames, coildatastructure["headrefdata"]["names"])
    coilindex = marker_indices(markernames, coildatastructure["coilrefdata"]["names"])

    if len(headindex) != len(coildatastructure["headrefdata"]["names"]):
        raise ValueError("Not all head markers were found in the marker frame.")
    if len(coilindex) != len(coildatastructure["coilrefdata"]["names"]):
        raise ValueError("Not all coil markers were found in the marker frame.")

    coildatastructure["headrefdata"]["data"] = marker_frame[:, headindex].T
    coil_exp_data = marker_frame[:, coilindex][np.newaxis, :, :]

    _, coildatastructure["headstimpointrefdata"], _, _ = rigidbodytransform(
        coildatastructure["coilrefdata"]["data"],
        coil_exp_data,
        coildatastructure["coilstimpointrefdata"]["data"])

    return coildatastructure


def _empty_marker_array():
    return np.empty((0, 3))


def sanitize_coildatastructure_for_save(coildatastructure):
    """
    Creates a serializable copy of the coil data structure while excluding
    live head-reference data and any head stimulation point data.
    """
    sanitized = {}
    for key in ["coilrefdata", "headrefdata", "coilstimpointrefdata"]:
        entry = coildatastructure.get(key, {})
        names = list(entry.get("names", []))
        data = np.asarray(entry.get("data", _empty_marker_array()), dtype=float)

        if key == "headrefdata":
            data = _empty_marker_array()

        sanitized[key] = {
            "names": names,
            "data": data.tolist()
        }

    sanitized.pop("headstimpoint", None)
    sanitized.pop("headstimpointrefdata", None)
    return sanitized


def _normalize_loaded_coildatastructure(raw_structure):
    normalized = {}
    for key in ["coilrefdata", "headrefdata", "coilstimpointrefdata"]:
        source_key = "stimpointrefdata" if key == "coilstimpointrefdata" else key
        entry = raw_structure.get(key, raw_structure.get(source_key, {}))
        names = list(entry.get("names", []))
        data = np.asarray(entry.get("data", []), dtype=float)

        if data.size == 0:
            data = _empty_marker_array()
        elif data.ndim == 1:
            data = data.reshape(1, -1)

        if key == "headrefdata":
            data = _empty_marker_array()

        normalized[key] = {
            "names": names,
            "data": data
        }
    return normalized


def save_coildatastructure(coildatastructure, filename):
    """
    Saves the coil data structure to JSON, excluding head reference data and
    any head stimulation point data.
    """
    serializable = sanitize_coildatastructure_for_save(coildatastructure)
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(serializable, file, indent=2)


def load_coildatastructure(filename):
    """
    Loads a coil data structure from JSON and restores numpy arrays.
    """
    with open(filename, "r", encoding="utf-8") as file:
        raw_structure = json.load(file)
    return _normalize_loaded_coildatastructure(raw_structure)


def sanitize_headrefdata_for_save(coildatastructure):
    """
    Creates a serializable copy of the coil data structure including
    head reference data and optional head stimulation point data.
    """
    sanitized = {}
    for key in ["coilrefdata", "headrefdata", "coilstimpointrefdata"]:
        entry = coildatastructure.get(key, {})
        names = list(entry.get("names", []))
        data = np.asarray(entry.get("data", _empty_marker_array()), dtype=float)
        sanitized[key] = {
            "names": names,
            "data": data.tolist()
        }

    headstimpointrefdata = coildatastructure.get("headstimpointrefdata")
    if headstimpointrefdata is not None:
        sanitized["headstimpointrefdata"] = np.asarray(
            headstimpointrefdata, dtype=float).tolist()

    return sanitized


def save_headrefdata(coildatastructure, filename):
    """
    Saves coil reference data together with head reference data and optional
    head stimulation point data.
    """
    serializable = sanitize_headrefdata_for_save(coildatastructure)
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(serializable, file, indent=2)


def load_headrefdata(filename):
    """
    Loads coil reference data together with head reference data and optional
    head stimulation point data.
    """
    with open(filename, "r", encoding="utf-8") as file:
        raw_structure = json.load(file)

    normalized = _normalize_loaded_coildatastructure(raw_structure)
    normalized["headrefdata"]["data"] = np.asarray(
        raw_structure.get("headrefdata", {}).get("data", []),
        dtype=float
    )
    if normalized["headrefdata"]["data"].size == 0:
        normalized["headrefdata"]["data"] = _empty_marker_array()
    elif normalized["headrefdata"]["data"].ndim == 1:
        normalized["headrefdata"]["data"] = normalized["headrefdata"]["data"].reshape(1, -1)

    if "headstimpointrefdata" in raw_structure:
        normalized["headstimpointrefdata"] = np.asarray(
            raw_structure["headstimpointrefdata"],
            dtype=float
        )

    return normalized


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
    if (coildatastructure["headrefdata"]['data'].size == 0 or
            "headstimpointrefdata" not in coildatastructure):
        coildatastructure = create_headrefdata(expfilename, coildatastructure)

    allmarkernames = coildatastructure["headrefdata"]["names"] + \
        coildatastructure["coilrefdata"]["names"]
    point_data, markernames, _ = getkindata(expfilename, allmarkernames)

    headrefdata = coildatastructure["headrefdata"]["data"]
    coilrefdata = coildatastructure["coilrefdata"]["data"]
    coilpoint = coildatastructure["coilstimpointrefdata"]["data"]
    headpoint = coildatastructure["headstimpointrefdata"]

    # get exp data
    coildisplacement = dict()
    coildisplacement["headmarkernames"] = coildatastructure["headrefdata"]["names"]
    coildisplacement["coilmarkernames"] = coildatastructure["coilrefdata"]["names"]
    headindex = marker_indices(markernames, coildatastructure["headrefdata"]["names"])
    coilindex = marker_indices(markernames, coildatastructure["coilrefdata"]["names"])
    coildisplacement["headexpdata"] = point_data.transpose(2, 0, 1)[:, 0:3, headindex]
    coildisplacement["coilexpdata"] = point_data.transpose(2, 0, 1)[:, 0:3, coilindex]

    # calculate stim point during exp
    coildisplacement['coilR'], coildisplacement["coilstimpoint"],_ ,_= rigidbodytransform(
        coilrefdata, coildisplacement["coilexpdata"], coilpoint)
    coildisplacement['headR'], coildisplacement["headstimpoint"], _, _ = rigidbodytransform(
        headrefdata, coildisplacement["headexpdata"], headpoint)

    return coildisplacement, coildatastructure


def get_coil_displacement_from_frame(markers, markernames, coildatastructure):
    """
    Computes coil displacement for a single in-memory frame.
    """
    required_markernames = (
        coildatastructure["headrefdata"]["names"] +
        coildatastructure["coilrefdata"]["names"]
    )
    all_indices = marker_indices(markernames, required_markernames)
    if len(all_indices) != len(required_markernames):
        missing = sorted(set(required_markernames) - set([markernames[i] for i in all_indices]))
        raise ValueError(f"Missing required markers in stream: {missing}")

    marker_frame = np.asarray(markers)
    if marker_frame.shape[0] != 3:
        raise ValueError("Expected markers with shape 3 x n_markers.")

    if coildatastructure["headrefdata"]['data'].size == 0:
        index = marker_indices(markernames, coildatastructure["headrefdata"]["names"])
        coildatastructure["headrefdata"]["data"] = marker_frame[:, index].T

    headrefdata = coildatastructure["headrefdata"]["data"]
    coilrefdata = coildatastructure["coilrefdata"]["data"]
    point = coildatastructure["coilstimpointrefdata"]["data"]

    coildisplacement = dict()
    coildisplacement["headmarkernames"] = coildatastructure["headrefdata"]["names"]
    coildisplacement["coilmarkernames"] = coildatastructure["coilrefdata"]["names"]
    headindex = marker_indices(markernames, coildatastructure["headrefdata"]["names"])
    coilindex = marker_indices(markernames, coildatastructure["coilrefdata"]["names"])
    coildisplacement["headexpdata"] = marker_frame[:, headindex][np.newaxis, :, :]
    coildisplacement["coilexpdata"] = marker_frame[:, coilindex][np.newaxis, :, :]

    coildisplacement['coilR'], coildisplacement["coilstimpoint"], _, _ = rigidbodytransform(
        coilrefdata, coildisplacement["coilexpdata"], point)
    headpoint = coildatastructure.get("headstimpointrefdata", coildisplacement["coilstimpoint"][0])
    coildisplacement['headR'], coildisplacement["headstimpoint"], _, _ = rigidbodytransform(
        headrefdata, coildisplacement["headexpdata"], headpoint)

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
