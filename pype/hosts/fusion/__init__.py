import sys
import os

from .pipeline import (
    install,
    uninstall,
    publish,
    launch_workfiles_app
)

from .utils import (
    setup
)


from .lib import (
    get_additional_data,
    update_frame_range
)

from .menu import launch_pype_menu

host_dir = os.path.dirname(__file__)
script_dir = os.path.join(host_dir, "scripts")
sys.path.append(script_dir)

__all__ = [
    # pipeline
    "install",
    "uninstall",
    "publish",
    "launch_workfiles_app",

    # utils
    "setup",
    "get_resolve_module",

    # lib
    "get_additional_data",
    "update_frame_range",

    # menu
    "launch_pype_menu",

    # scripts
    "set_rendermode"
]
