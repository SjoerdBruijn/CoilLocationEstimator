import os

backend = os.environ.get("COIL_ANIMATION_BACKEND", "matplotlib").strip().lower()

if backend in {"pyvista", "pyvistaqt", "qt"}:
    try:
        from .PyVistaAnimationApp import AnimationApp
    except ImportError:
        from PyVistaAnimationApp import AnimationApp
else:
    try:
        from .CoilLocationAnimationApp import AnimationApp
    except ImportError:
        from CoilLocationAnimationApp import AnimationApp
