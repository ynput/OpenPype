# -*- coding: utf-8 -*-
"""Open install dialog."""

import os
import sys

os.chdir(os.path.dirname(__file__))  # for override sys.path in Deadline

from .bootstrap_repos import (
    BootstrapRepos,
    OpenPypeVersion
)
from .version import __version__ as version

# Store OpenPypeVersion to 'sys.modules'
#   - this makes it available in OpenPype processes without modifying
#       'sys.path' or 'PYTHONPATH'
if "OpenPypeVersion" not in sys.modules:
    sys.modules["OpenPypeVersion"] = OpenPypeVersion


def _get_qt_app():
    from qtpy import QtWidgets, QtCore

    is_event_loop_running = True

    app = QtWidgets.QApplication.instance()
    if app is not None:
        return app, is_event_loop_running

    for attr_name in (
        "AA_EnableHighDpiScaling",
        "AA_UseHighDpiPixmaps",
    ):
        attr = getattr(QtCore.Qt, attr_name, None)
        if attr is not None:
            QtWidgets.QApplication.setAttribute(attr)

    if hasattr(QtWidgets.QApplication, "setHighDpiScaleFactorRoundingPolicy"):
        QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    # Since it's a new QApplication the event loop isn't running yet
    is_event_loop_running = False

    return QtWidgets.QApplication(sys.argv), is_event_loop_running


def open_dialog():
    """Show Igniter dialog."""
    if os.getenv("OPENPYPE_HEADLESS_MODE"):
        print("!!! Can't open dialog in headless mode. Exiting.")
        sys.exit(1)
    from .install_dialog import InstallDialog

    app, is_event_loop_running = _get_qt_app()

    d = InstallDialog()
    d.open()

    if not is_event_loop_running:
        app.exec_()
    else:
        d.exec_()

    return d.result()


def open_update_window(openpype_version, zxp_hosts=None):
    """Open update window."""
    if zxp_hosts is None:
        zxp_hosts = []
    if os.getenv("OPENPYPE_HEADLESS_MODE"):
        print("!!! Can't open dialog in headless mode. Exiting.")
        sys.exit(1)

    from .update_window import UpdateWindow

    app, is_event_loop_running = _get_qt_app()

    d = UpdateWindow(version=openpype_version, zxp_hosts=zxp_hosts)
    d.open()

    if not is_event_loop_running:
        app.exec_()
    else:
        d.exec_()

    version_path = d.get_version_path()
    return version_path


def show_message_dialog(title, message):
    """Show dialog with a message and title to user."""
    if os.getenv("OPENPYPE_HEADLESS_MODE"):
        print("!!! Can't open dialog in headless mode. Exiting.")
        sys.exit(1)

    from .message_dialog import MessageDialog

    app, is_event_loop_running = _get_qt_app()

    dialog = MessageDialog(title, message)
    dialog.open()

    if not is_event_loop_running:
        app.exec_()
    else:
        dialog.exec_()


__all__ = [
    "BootstrapRepos",
    "open_dialog",
    "open_update_window",
    "show_message_dialog",
    "version"
]
