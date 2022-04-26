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


def open_dialog():
    """Show Igniter dialog."""
    if os.getenv("OPENPYPE_HEADLESS_MODE"):
        print("!!! Can't open dialog in headless mode. Exiting.")
        sys.exit(1)
    from Qt import QtWidgets, QtCore
    from .install_dialog import InstallDialog

    scale_attr = getattr(QtCore.Qt, "AA_EnableHighDpiScaling", None)
    if scale_attr is not None:
        QtWidgets.QApplication.setAttribute(scale_attr)

    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    d = InstallDialog()
    d.open()

    app.exec_()
    return d.result()


def open_update_window(openpype_version):
    """Open update window."""
    if os.getenv("OPENPYPE_HEADLESS_MODE"):
        print("!!! Can't open dialog in headless mode. Exiting.")
        sys.exit(1)
    from Qt import QtWidgets, QtCore
    from .update_window import UpdateWindow

    scale_attr = getattr(QtCore.Qt, "AA_EnableHighDpiScaling", None)
    if scale_attr is not None:
        QtWidgets.QApplication.setAttribute(scale_attr)

    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    d = UpdateWindow(version=openpype_version)
    d.open()

    app.exec_()
    version_path = d.get_version_path()
    return version_path


def show_message_dialog(title, message):
    """Show dialog with a message and title to user."""
    if os.getenv("OPENPYPE_HEADLESS_MODE"):
        print("!!! Can't open dialog in headless mode. Exiting.")
        sys.exit(1)
    from Qt import QtWidgets, QtCore
    from .message_dialog import MessageDialog

    scale_attr = getattr(QtCore.Qt, "AA_EnableHighDpiScaling", None)
    if scale_attr is not None:
        QtWidgets.QApplication.setAttribute(scale_attr)

    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    dialog = MessageDialog(title, message)
    dialog.open()

    app.exec_()


__all__ = [
    "BootstrapRepos",
    "open_dialog",
    "open_update_window",
    "show_message_dialog",
    "version"
]
