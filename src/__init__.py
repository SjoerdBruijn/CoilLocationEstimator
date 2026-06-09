"""Public package interface for CoilLocationEstimator."""

from .LSLHelper import main as _lsl_helper_main

from .CoilLocationFcns import (
	create_coil_data,
	create_headrefdata,
	get_coil_displacement,
	getkindata,
	load_coildatastructure,
	marker_indices,
	save_coildatastructure,
	save_headrefdata,
)


def lsl_helper(argv=None):
	"""Run unified LSL helper modes from the package namespace.

	Examples
	--------
	- lsl_helper(["viewer"])
	- lsl_helper(["streamer"])
	- lsl_helper(["--list-streams"])
	"""
	return _lsl_helper_main(argv)

__all__ = [
	"create_coil_data",
	"create_headrefdata",
	"get_coil_displacement",
	"getkindata",
	"load_coildatastructure",
	"lsl_helper",
	"marker_indices",
	"save_coildatastructure",
	"save_headrefdata",
]
