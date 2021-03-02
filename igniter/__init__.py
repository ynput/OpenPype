# -*- coding: utf-8 -*-
"""Open install dialog."""

import sys
from Qt import QtWidgets

from .install_dialog import InstallDialog
from .bootstrap_repos import BootstrapRepos


def run():
    """Show Igniter dialog."""
    app = QtWidgets.QApplication(sys.argv)
    d = InstallDialog()
    d.show()
    sys.exit(app.exec_())


__all__ = [
    "InstallDialog",
    "BootstrapRepos",
    "run"
]
