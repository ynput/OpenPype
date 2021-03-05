# -*- coding: utf-8 -*-
"""Open install dialog."""

import sys
from Qt import QtWidgets  # noqa
from Qt.QtCore import Signal  # noqa

from .install_dialog import InstallDialog
from .bootstrap_repos import BootstrapRepos


RESULT = 0


def get_result(res: int):
    """Sets result returned from dialog."""
    global RESULT
    RESULT = res


def run():
    """Show Igniter dialog."""
    app = QtWidgets.QApplication(sys.argv)
    d = InstallDialog()
    d.finished.connect(get_result)
    d.show()
    app.exec_()
    return RESULT


__all__ = [
    "InstallDialog",
    "BootstrapRepos",
    "run"
]
