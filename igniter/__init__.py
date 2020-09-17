# -*- coding: utf-8 -*-
"""Open install dialog."""

import sys
from Qt import QtWidgets

from .install_dialog import InstallDialog


def run():
    app = QtWidgets.QApplication(sys.argv)
    d = InstallDialog()
    d.show()
    sys.exit(app.exec_())
