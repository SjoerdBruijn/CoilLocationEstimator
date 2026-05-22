# Coil Location Estimator

Tools for estimating TMS coil location from C3D motion-capture data, creating
coil/head reference data structures, visualizing coil displacement, and testing
live tracking through LSL.

## Installation

1. Clone or download this repository.
2. Open a terminal in the project directory.
3. Create and activate a Python virtual environment:

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
- pylsl
- pyvista, pyvistaqt, PyQt5, and qtpy for the optional PyVista/Qt animation backend

Tkinter is also used by the GUIs. It is included with many Python installs, but
some Python distributions require installing Tk support separately.

## Usage

### Main Example

Run the scripted example:

```sh
python MainExamples.py
```

Update the C3D filenames and marker names in `MainExamples.py` before running it
on your own data. The example creates a coil data structure, creates head
reference data, computes displacement for an experimental file, and opens the
animation app.

By default the animation uses the Matplotlib/Tk backend. To use the PyVista/Qt
backend instead:

```sh
COIL_ANIMATION_BACKEND=pyvista python MainExamples.py
```

### Offline GUI

Run the offline estimator GUI directly:

```sh
python src/CoilLocationGUI.py
```

Typical workflow:

1. Select a coil reference C3D file.
2. Create, load, or save the coil data structure.
3. Select a head reference C3D file.
4. Create, load, or save the head reference data structure.
5. Select an experimental C3D file.
6. Click **Show Data** to compute and visualize coil displacement.
7. Optionally enable **Save Results** before showing data to save the computed
   displacement and reference data to JSON.

### Realtime GUI

Run the realtime LSL GUI directly:

```sh
python src/realtimeGUI.py
```

Typical workflow:

1. Select a coil reference C3D file and create or load the coil data structure.
2. Select a head reference C3D file and create or load the head reference data
   structure.
3. Connect to an LSL marker stream.
4. Start **Live View**.

The realtime GUI expects the same marker names to be available in the LSL stream
metadata or inferred from channel order.

### Testing Realtime With C3DToLSLStreamer

You can test the realtime GUI without a motion-capture system by replaying a C3D
file over LSL with the included streamer app.

In one terminal:

```sh
python src/C3DToLSLStreamer.py
```

Select a C3D file and click **Start Streaming**. Then, in another terminal, run:

```sh
python src/realtimeGUI.py
```

Click **Connect to LSL** in the realtime GUI and use the streamed C3D data as
the live marker source.

### Marker Names Utility

To inspect marker names advertised by an LSL stream:

```sh
python src/LSLMarkerNamesViewer.py
```

or from the command line:

```sh
python src/LSLMarkerNamesCLI.py --list-streams
```

### Kabsch Test

Run the rigid-body transform test script:

```sh
python TestKabsch.py
```

## Project Structure

- `MainExamples.py` - Scripted example for coil location estimation and animation.
- `TestKabsch.py` - Test script for the rigid-body transform implementation.
- `src/CoilLocationFcns.py` - Core marker selection, reference-data, displacement, and save/load functions.
- `src/CoilLocationGUI.py` - Offline GUI.
- `src/realtimeGUI.py` - Realtime LSL GUI.
- `src/C3DToLSLStreamer.py` - Small app for replaying C3D marker data over LSL.
- `src/CoilLocationAnimationApp.py` - Matplotlib/Tk animation backend.
- `src/PyVistaAnimationApp.py` - Optional PyVista/Qt animation backend.
- `src/AnimationBackend.py` - Backend selector controlled by `COIL_ANIMATION_BACKEND`.
- `requirements.txt` - Python dependencies.

## Notes

- Coil data structures and head reference data can be saved as JSON from both GUIs.
- Plain coil data saves intentionally omit head reference samples; save head
  reference data separately when you want to reuse a head reference.
- If you add dependencies, update `requirements.txt`.

## License

MIT License
