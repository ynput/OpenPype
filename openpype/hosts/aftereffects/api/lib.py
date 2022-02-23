import os
import sys
import contextlib
import traceback
import logging

from Qt import QtWidgets

from openpype.lib.remote_publish import headless_publish

from openpype.tools.utils import host_tools
from .launch_logic import ProcessLauncher, get_stub

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def safe_excepthook(*args):
    traceback.print_exception(*args)


def main(*subprocess_args):
    sys.excepthook = safe_excepthook

    import avalon.api
    from openpype.hosts.aftereffects import api

    avalon.api.install(api)

    os.environ["OPENPYPE_LOG_NO_COLORS"] = "False"
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)

    launcher = ProcessLauncher(subprocess_args)
    launcher.start()

    if os.environ.get("HEADLESS_PUBLISH"):
        launcher.execute_in_main_thread(lambda: headless_publish(
            log,
            "CloseAE",
            os.environ.get("IS_TEST")))
    elif os.environ.get("AVALON_PHOTOSHOP_WORKFILES_ON_LAUNCH", True):
        save = False
        if os.getenv("WORKFILES_SAVE_AS"):
            save = True

        launcher.execute_in_main_thread(
            lambda: host_tools.show_tool_by_name("workfiles", save=save)
        )

    sys.exit(app.exec_())


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context."""
    selection = get_stub().get_selected_items(True, False, False)
    try:
        yield selection
    finally:
        pass


def get_extension_manifest_path():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "extension",
        "CSXS",
        "manifest.xml"
    )
