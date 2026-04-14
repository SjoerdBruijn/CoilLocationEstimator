# Coil Location Estimator

This package provides tools for estimating coil locations from C3D motion capture files, visualizing coil movement, and running Kabsch algorithm tests. * UNDER CONSTRUCTION *

## Installation

1. **Clone or download this repository.**
2. Open a terminal in the project directory.
3. Create and activate a Python virtual environment (recommended):

```sh
python3 -m venv .venv
source .venv/bin/activate
```

4. Install the required dependencies:

```sh
pip install -r requirements.txt
```

## Requirements
- Python 3.8+
- ezc3d
- matplotlib
- numpy

## Usage

### Main Example
To run the main example (process and animate coil location data):

```sh
python MainExamples.py
```

- Make sure your `.c3d` files (e.g., `Jen Cal 05.c3d`, `Jen Cal 08.c3d`) are in the project directory.
- The script will visualize coil displacement using a Tkinter/matplotlib animation window.

### Kabsch Test
To test the Kabsch algorithm implementation:

```sh
python TestKabsch.py
```

### GUI
To use the graphical user interface for coil location estimation, uncomment the `estimatorgui()` line in `MainExamples.py` or run the GUI directly:

```sh
python -c "from CoilLocationGUI import estimatorgui; estimatorgui()"
```

## Project Structure
- `MainExamples.py` — Main example script for coil location estimation and animation.
- `TestKabsch.py` — Test script for the Kabsch algorithm.
- `src/` — Source code for coil location functions, GUI, and animation.
- `requirements.txt` — List of required Python packages.

## Notes
- If you add new dependencies, update `requirements.txt` accordingly.
- For best results, use the provided virtual environment and requirements file.

## License
MIT License
