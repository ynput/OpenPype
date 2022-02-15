import os
import sys
import contextlib
import traceback

from Qt import QtWidgets

import avalon.api

from openpype.api import Logger
from openpype.tools.utils import host_tools
from openpype.lib.remote_publish import headless_publish
from openpype.lib import env_value_to_bool

from .launch_logic import ProcessLauncher, stub

log = Logger.get_logger(__name__)


def safe_excepthook(*args):
    traceback.print_exception(*args)


def main(*subprocess_args):
    from openpype.hosts.photoshop import api

    avalon.api.install(api)
    sys.excepthook = safe_excepthook

    # coloring in StdOutBroker
    os.environ["OPENPYPE_LOG_NO_COLORS"] = "False"
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)

    launcher = ProcessLauncher(subprocess_args)
    launcher.start()

    if env_value_to_bool("HEADLESS_PUBLISH"):
        launcher.execute_in_main_thread(
            headless_publish,
            log,
            "ClosePS",
            os.environ.get("IS_TEST")
        )
    elif env_value_to_bool("AVALON_PHOTOSHOP_WORKFILES_ON_LAUNCH",
                           default=True):

        launcher.execute_in_main_thread(
            host_tools.show_workfiles,
            save=env_value_to_bool("WORKFILES_SAVE_AS")
        )

    sys.exit(app.exec_())


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context."""
    selection = stub().get_selected_layers()
    try:
        yield selection
    finally:
        stub().select_layers(selection)


@contextlib.contextmanager
def maintained_visibility():
    """Maintain visibility during context."""
    visibility = {}
    layers = stub().get_layers()
    for layer in layers:
        visibility[layer.id] = layer.visible
    try:
        yield
    finally:
        for layer in layers:
            stub().set_visible(layer.id, visibility[layer.id])
            pass
