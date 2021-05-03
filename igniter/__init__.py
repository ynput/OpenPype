# -*- coding: utf-8 -*-
"""Open install dialog."""

import os
import sys

os.chdir(os.path.dirname(__file__))  # for override sys.path in Deadline

from .bootstrap_repos import BootstrapRepos
from .version import __version__ as version


def open_dialog():
    """Show Igniter dialog."""
    from Qt import QtWidgets, QtCore
    from .install_dialog import InstallDialog

    scale_attr = getattr(QtCore.Qt, "AA_EnableHighDpiScaling", None)
    if scale_attr is not None:
        QtWidgets.QApplication.setAttribute(scale_attr)

    app = QtWidgets.QApplication(sys.argv)

    d = InstallDialog()
    d.open()

    app.exec_()
    return d.result()


__all__ = [
    "BootstrapRepos",
    "open_dialog",
    "version"
]
