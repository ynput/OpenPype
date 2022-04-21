import sys
import logging

from avalon import api

from openpype.pipeline import registered_host
from openpype.tools.utils import qt_app_context
from .window import Window

log = logging.getLogger(__name__)

module = sys.modules[__name__]
module.window = None


def validate_host_requirements(host):
    if host is None:
        raise RuntimeError("No registered host.")

    # Verify the host has implemented the api for Work Files
    required = [
        "open_file",
        "save_file",
        "current_file",
        "has_unsaved_changes",
        "work_root",
        "file_extensions",
    ]
    missing = []
    for name in required:
        if not hasattr(host, name):
            missing.append(name)
    if missing:
        raise RuntimeError(
            "Host is missing required Work Files interfaces: "
            "%s (host: %s)" % (", ".join(missing), host)
        )
    return True


def show(root=None, debug=False, parent=None, use_context=True, save=True):
    """Show Work Files GUI"""
    # todo: remove `root` argument to show()

    try:
        module.window.close()
        del(module.window)
    except (AttributeError, RuntimeError):
        pass

    host = registered_host()
    validate_host_requirements(host)

    if debug:
        api.Session["AVALON_ASSET"] = "Mock"
        api.Session["AVALON_TASK"] = "Testing"

    with qt_app_context():
        window = Window(parent=parent)
        window.refresh()

        if use_context:
            context = {
                "asset": api.Session["AVALON_ASSET"],
                "task": api.Session["AVALON_TASK"]
            }
            window.set_context(context)

        window.set_save_enabled(save)

        window.show()

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()
