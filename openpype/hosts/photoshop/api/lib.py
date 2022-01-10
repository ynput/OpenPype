import os
import sys
import contextlib
import logging
import traceback

from Qt import QtWidgets

from openpype.tools.utils import host_tools

from openpype.lib.remote_publish import headless_publish

from .launch_logic import ProcessLauncher, stub

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def safe_excepthook(*args):
    traceback.print_exception(*args)


def main(*subprocess_args):
    from avalon import api, photoshop

    api.install(photoshop)
    sys.excepthook = safe_excepthook

    # coloring in ConsoleTrayApp
    os.environ["OPENPYPE_LOG_NO_COLORS"] = "False"
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)

    launcher = ProcessLauncher(subprocess_args)
    launcher.start()

    if os.environ.get("HEADLESS_PUBLISH"):
        launcher.execute_in_main_thread(lambda: headless_publish(
            log,
            "ClosePS",
            os.environ.get("IS_TEST")))
    elif os.environ.get("AVALON_PHOTOSHOP_WORKFILES_ON_LAUNCH", True):
        save = False
        if os.getenv("WORKFILES_SAVE_AS"):
            save = True

        launcher.execute_in_main_thread(
            lambda: host_tools.show_workfiles(save=save)
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
