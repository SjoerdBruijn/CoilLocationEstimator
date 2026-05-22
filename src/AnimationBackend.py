import os

backend = os.environ.get("COIL_ANIMATION_BACKEND", "matplotlib").strip().lower()

if backend in {"pyvista", "pyvistaqt", "qt"}:
    from PyVistaAnimationApp import AnimationApp
else:
    from CoilLocationAnimationApp import AnimationApp
