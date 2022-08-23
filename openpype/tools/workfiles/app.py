import sys
import logging

from openpype.host import IWorkfileHost
from openpype.pipeline import (
    registered_host,
    legacy_io,
)
from openpype.tools.utils import qt_app_context
from .window import Window

log = logging.getLogger(__name__)

module = sys.modules[__name__]
module.window = None


def show(root=None, debug=False, parent=None, use_context=True, save=True):
    """Show Work Files GUI"""
    # todo: remove `root` argument to show()

    try:
        module.window.close()
        del(module.window)
    except (AttributeError, RuntimeError):
        pass

    host = registered_host()
    IWorkfileHost.validate_workfile_methods(host)

    if debug:
        legacy_io.Session["AVALON_ASSET"] = "Mock"
        legacy_io.Session["AVALON_TASK"] = "Testing"

    with qt_app_context():
        window = Window(parent=parent)
        window.refresh()

        if use_context:
            context = {
                "asset": legacy_io.Session["AVALON_ASSET"],
                "task": legacy_io.Session["AVALON_TASK"]
            }
            window.set_context(context)

        window.set_save_enabled(save)

        window.show()

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()
