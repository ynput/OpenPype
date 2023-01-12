# -*- coding: utf-8 -*-
"""Open install dialog."""

import sys
from qtpy import QtWidgets

from .install_dialog import InstallDialog


RESULT = 0


def get_result(res: int):
    """Sets result returned from dialog."""
    global RESULT
    RESULT = res


app = QtWidgets.QApplication(sys.argv)

d = InstallDialog()
d.finished.connect(get_result)
d.open()
app.exec()
sys.exit(RESULT)
