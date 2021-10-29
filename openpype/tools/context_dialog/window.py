import os
import json

from Qt import QtWidgets, QtCore, QtGui
from avalon.api import AvalonMongoDB

from openpype import style


class ContextDialog(QtWidgets.QDialog):
    """Dialog to select a context.

    Context has 3 parts:
    - Project
    - Aseet
    - Task

    It is possible to predefine project and asset. In that case their widgets
    will have passed preselected values and will be disabled.
    """
    def __init__(self, parent=None):
        super(ContextDialog, self).__init__(parent)

        self.setWindowTitle("Select Context")
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))

        # Enable minimize and maximize for app
        window_flags = QtCore.Qt.Window
        if not parent:
            window_flags |= QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(window_flags)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        dbcon = AvalonMongoDB()

        # Output of dialog
        self._context_to_store = {
            "project": None,
            "asset": None,
            "task": None
        }

    def get_context(self):
        return self._context_to_store


def main(
    path_to_store,
    project_name=None,
    asset_name=None,
    strict=True
):
    app = QtWidgets.QApplication([])
    window = ContextDialog()
    window.show()
    app.exec_()

    data = window.get_context()

    file_dir = os.path.dirname(path_to_store)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)

    with open(path_to_store, "w") as stream:
        json.dump(data, stream)
