# -*- coding: utf-8 -*-
"""Open install dialog."""

import os
import sys

os.chdir(os.path.dirname(__file__))  # for override sys.path in Deadline

from .bootstrap_repos import BootstrapRepos
from .version import __version__ as version


RESULT = 0


def get_result(res: int):
    """Sets result returned from dialog."""
    global RESULT
    RESULT = res


def open_dialog():
    """Show Igniter dialog."""
    from Qt import QtWidgets
    from .install_dialog import InstallDialog

    app = QtWidgets.QApplication(sys.argv)

    d = InstallDialog()
    d.finished.connect(get_result)
    d.open()

    app.exec()

    return RESULT


__all__ = [
    "InstallDialog",
    "BootstrapRepos",
    "open_dialog",
    "version"
]
