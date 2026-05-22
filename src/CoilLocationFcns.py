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
    Launch a GUI to choose coil, head, and stimulation marker names from a C3D file.

    Args:
        filename (str): Path to the C3D file used for marker selection.
        coilmarkernames (list[str]): Preselected coil marker names.
        headmarkernames (list[str]): Preselected head marker names.
        stimpointmarkername (list[str]): Preselected coil stimulation marker names.

    Returns:
        tuple: Selected coil marker names, head marker names, and coil
            stimulation marker names. The C3D data itself is not modified.
    """
    point_data, markernames, firstind = getkindata(filename)
    markerselector = MarkerSelector(point_data[:,:,firstind], markernames,
                                    coilmarkernames,
                                    headmarkernames,
                                    stimpointmarkername)
    coilmarkernames, headmarkernames, stimpointmarkername = markerselector.get_marker_names()
    return coilmarkernames, headmarkernames, stimpointmarkername


def marker_indices(markernames, names_to_find):
    """
    Find marker-name indices using case-insensitive suffix matching.

    Args:
        markernames (list[str]): Full marker labels from a C3D file or stream.
        names_to_find (list[str]): Marker labels to locate.

    Returns:
        list[int]: Indices in ``markernames`` for every found name. Missing
            names are printed and omitted from the result.
    """
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
    """
    Extract one sample of XYZ marker coordinates from C3D point data.

    Args:
        point_data (np.ndarray): C3D points array with dimensions compatible
            with ezc3d output, typically 4 x n_markers x n_frames.
        firstind (int): Frame index to extract.
        indices (list[int]): Marker indices to extract.

    Returns:
        np.ndarray: Extracted marker coordinates with shape n_markers x 3.
    """
    return point_data.transpose(2, 0, 1)[firstind, 0:3, indices].T

def getkindata(filename, selectedmarkernames=None):
    """
    Load C3D point data and find the first usable frame for selected markers.

    Args:
        filename (str): Path to the C3D file.
        selectedmarkernames (list[str] | None): Marker names used to test
            visibility. If None, all markers in the file are considered.

    Returns:
        tuple: ``(point_data, markernames, firstind)`` where ``point_data`` is
            the ezc3d point array, ``markernames`` is the file label list, and
            ``firstind`` is the first frame where selected markers are visible.
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
    Create a coil data structure from a reference C3D file.

    Args:
        filename (str): Path to the coil reference C3D file.
        coilmarkernames (list[str] | None): Coil marker names. If empty, the
            marker selector is opened.
        headmarkernames (list[str] | None): Head marker names. If empty, the
            marker selector is opened.
        stimpointmarkername (list[str] | None): Coil stimulation marker names.
            If empty, the marker selector is opened.

    Returns:
        dict: Coil data structure containing marker names and reference
            coordinate arrays for ``coilrefdata``, ``headrefdata``, and
            ``coilstimpointrefdata``. Data are taken from the first frame where
            all selected markers are visible.
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


def create_headrefdata(filename, coildatastructure, sample_number=None):
    """
    Add head-reference data from a C3D file to an existing coil data structure.

    Args:
        filename (str): Path to the head-reference C3D file.
        coildatastructure (dict): Coil data structure created by
            ``create_coil_data`` or loaded from JSON.
        sample_number (int | None): Zero-based frame index to use as the head
            reference. If None, uses the first frame where required markers are
            visible.

    Returns:
        dict: The same ``coildatastructure`` object, updated in place with
            ``headrefdata["data"]`` and ``headstimpointrefdata``. The head
            stimulation reference point is computed by transforming
            ``coilstimpointrefdata`` to the coil pose at ``sample_number``.

    Raises:
        IndexError: If ``sample_number`` is outside the C3D frame range.
        ValueError: If required head or coil markers are missing.
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

    experimental_coildata = point_data.transpose(2, 0, 1)[:, 0:3, coilindex]

    _,  coildatastructure["headstimpointrefdata"], _, _ = rigidbodytransform(
        coildatastructure["coilrefdata"]["data"],
        experimental_coildata[sample_number:sample_number + 1],
        coildatastructure["coilstimpointrefdata"]["data"])
    
    return coildatastructure


def _empty_marker_array():
    """
    Create the canonical empty marker-coordinate array.

    Returns:
        np.ndarray: Empty float array with shape 0 x 3, used when reference
            marker data is intentionally absent.
    """
    return np.empty((0, 3))


def sanitize_coildatastructure_for_save(coildatastructure):
    """
    Convert coil reference data to a JSON-serializable dictionary.

    Args:
        coildatastructure (dict): Runtime coil data structure containing numpy
            arrays.

    Returns:
        dict: Serializable copy that preserves coil and coil-stim reference data
            while clearing ``headrefdata["data"]`` and omitting any head
            stimulation reference fields.
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
    """
    Normalize a JSON-loaded coil data structure into runtime numpy arrays.

    Args:
        raw_structure (dict): Dictionary read from a JSON coil-data file. Both
            legacy ``stimpointrefdata`` and current ``coilstimpointrefdata`` are
            accepted.

    Returns:
        dict: Normalized coil data structure with numpy arrays. Head reference
            data is deliberately cleared to an empty 0 x 3 array for plain coil
            data loads.
    """
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
    Save coil reference data to JSON without head-reference data.

    Args:
        coildatastructure (dict): Runtime coil data structure to serialize.
        filename (str): Output JSON path.

    Returns:
        None: Writes a JSON file and does not mutate ``coildatastructure``.
    """
    serializable = sanitize_coildatastructure_for_save(coildatastructure)
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(serializable, file, indent=2)


def load_coildatastructure(filename):
    """
    Load coil reference data from JSON.

    Args:
        filename (str): Path to a JSON file created by
            ``save_coildatastructure`` or an older compatible version.

    Returns:
        dict: Runtime coil data structure with numpy arrays. Head reference
            coordinate data is cleared to the canonical empty 0 x 3 array.
    """
    with open(filename, "r", encoding="utf-8") as file:
        raw_structure = json.load(file)
    return _normalize_loaded_coildatastructure(raw_structure)


def sanitize_headrefdata_for_save(coildatastructure):
    """
    Convert coil and head reference data to a JSON-serializable dictionary.

    Args:
        coildatastructure (dict): Runtime coil data structure containing head
            reference data and optionally ``headstimpointrefdata``.

    Returns:
        dict: Serializable copy including all reference arrays needed to reuse
            the head reference later.
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
    Save coil and head reference data to JSON.

    Args:
        coildatastructure (dict): Runtime coil data structure containing
            ``headrefdata`` and ``headstimpointrefdata``.
        filename (str): Output JSON path.

    Returns:
        None: Writes a JSON file and does not mutate ``coildatastructure``.
    """
    serializable = sanitize_headrefdata_for_save(coildatastructure)
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(serializable, file, indent=2)


def load_headrefdata(filename):
    """
    Load coil and head reference data from JSON.

    Args:
        filename (str): Path to a JSON file created by ``save_headrefdata``.

    Returns:
        dict: Runtime coil data structure with numpy arrays, including
            ``headrefdata["data"]`` and ``headstimpointrefdata`` when present.
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


def _make_json_serializable(value):
    """
    Convert runtime result data into JSON-compatible Python containers.

    Args:
        value: Any value from a coil displacement or coil data structure,
            including dictionaries, lists, tuples, numpy arrays, and numpy scalar
            types.

    Returns:
        object: A JSON-serializable version of ``value``. Numpy arrays become
            nested lists, numpy scalars become native Python scalars, and
            dictionaries/lists are converted recursively without mutating the
            original data.
    """
    if isinstance(value, dict):
        return {key: _make_json_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_serializable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def save_results(coildisplacement, coildatastructure=None, filename=None):
    """
    Save computed coil displacement results to a JSON file.

    Args:
        coildisplacement (dict): Result dictionary returned by
            ``get_coil_displacement`` or ``get_coil_displacement_from_frame``.
        coildatastructure (dict | None): Optional reference data structure to
            save alongside the computed displacement data.
        filename (str | None): Destination path. If None, a save-file dialog is
            opened and the user is asked where to save the results.

    Returns:
        str | None: The path written, or None if the user cancels the save
            dialog. The input dictionaries are not modified.
    """
    if filename is None:
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            title="Save coil displacement results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
    if not filename:
        return None

    results = {"coildisplacement": coildisplacement}
    if coildatastructure is not None:
        results["coildatastructure"] = coildatastructure

    with open(filename, "w") as file:
        json.dump(_make_json_serializable(results), file, indent=2)
    return filename


def get_coil_displacement(expfilename, coildatastructure):
    """
    Compute head and coil motion across an experimental C3D file.

    Args:
        expfilename (str): Path to the experimental C3D file.
        coildatastructure (dict): Coil/head reference structure containing coil
            reference data, head reference data, coil stimulation point reference
            data, and head stimulation point reference data.

    Returns:
        tuple: ``(coildisplacement, coildatastructure)``. ``coildisplacement``
            contains experimental marker arrays (``headexpdata`` and
            ``coilexpdata``), transformed stimulation point trajectories, marker
            names, and rigid-body rotations. ``coildatastructure`` is returned
            unchanged.

    Raises:
        ValueError: If head reference data or head stimulation point reference
            data are missing.
    """
    if coildatastructure["headrefdata"]['data'].size == 0:
        raise ValueError("Create or load head reference data before showing experimental data.")
    if "headstimpointrefdata" not in coildatastructure:
        raise ValueError("Create or load head stimulation point reference data before showing experimental data.")

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
    Compute head and coil displacement for one in-memory marker frame.

    Args:
        markers (np.ndarray): Current marker coordinates with shape 3 x n_markers.
        markernames (list[str]): Names corresponding to marker columns.
        coildatastructure (dict): Coil/head reference structure.

    Returns:
        tuple: ``(coildisplacement, coildatastructure)`` for a single frame.
            The displacement dictionary has one-sample arrays for
            ``headexpdata``, ``coilexpdata``, ``headstimpoint``, and
            ``coilstimpoint``. The input ``coildatastructure`` is returned
            unchanged.

    Raises:
        ValueError: If the marker frame has an invalid shape or required
            markers, head reference data, or head stimulation point reference
            data are missing.
    """
    if coildatastructure["headrefdata"]["data"].size == 0:
        raise ValueError("Create or load head reference data before live tracking.")
    if "headstimpointrefdata" not in coildatastructure:
        raise ValueError("Create or load head stimulation point reference data before live tracking.")

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

    headrefdata = coildatastructure["headrefdata"]["data"]
    coilrefdata = coildatastructure["coilrefdata"]["data"]
    point = coildatastructure["coilstimpointrefdata"]["data"]
    headpoint = coildatastructure["headstimpointrefdata"]

    coildisplacement = dict()
    coildisplacement["headmarkernames"] = coildatastructure["headrefdata"]["names"]
    coildisplacement["coilmarkernames"] = coildatastructure["coilrefdata"]["names"]
    headindex = marker_indices(markernames, coildatastructure["headrefdata"]["names"])
    coilindex = marker_indices(markernames, coildatastructure["coilrefdata"]["names"])
    coildisplacement["headexpdata"] = marker_frame[:, headindex][np.newaxis, :, :]
    coildisplacement["coilexpdata"] = marker_frame[:, coilindex][np.newaxis, :, :]

    coildisplacement['coilR'], coildisplacement["coilstimpoint"], _, _ = rigidbodytransform(
        coilrefdata, coildisplacement["coilexpdata"], point)
    coildisplacement['headR'], coildisplacement["headstimpoint"], _, _ = rigidbodytransform(
        headrefdata, coildisplacement["headexpdata"], headpoint)

    return coildisplacement, coildatastructure


def rigidbodytransform(A, B, virt_marker=None):
    """
    Align reference markers to experimental markers with a rigid-body transform.

    Args:
        A (np.ndarray): Reference marker coordinates as n_samples x 3 x
            n_markers, or a single 3 x n_markers / n_markers x 3 reference pose
            that can be tiled across samples.
        B (np.ndarray): Target marker coordinates with shape n_samples x 3 x
            n_markers. Samples with fewer than three visible markers are left as
            NaN in the outputs.
        virt_marker (np.ndarray | None): Optional virtual marker coordinates in
            the coordinate system of ``A``. If provided, these points are
            transformed into the coordinate system of each ``B`` sample.

    Returns:
        tuple: ``(R, virt_marker_in_B, t, rmsd)`` where ``R`` contains rotation
            matrices, ``virt_marker_in_B`` contains transformed virtual marker
            positions, ``t`` contains translations, and ``rmsd`` contains
            per-sample residual error.
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
