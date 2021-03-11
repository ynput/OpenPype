# -*- coding: utf-8 -*-
"""Open install dialog."""

import sys

import os
os.chdir(os.path.dirname(__file__))  # for override sys.path in Deadline

from Qt import QtWidgets  # noqa
from Qt.QtCore import Signal  # noqa

from .install_dialog import InstallDialog
from .bootstrap_repos import BootstrapRepos
from .version import __version__ as version


RESULT = 0


def get_result(res: int):
    """Sets result returned from dialog."""
    global RESULT
    RESULT = res


def open_dialog():
    """Show Igniter dialog."""
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
