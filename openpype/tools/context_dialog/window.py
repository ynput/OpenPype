from Qt import QtWidgets, QtCore, QtGui


class ContextDialog(QtWidgets.QDialog):
    """Dialog to select a context.

    Context has 3 parts:
    - Project
    - Aseet
    - Task

    It is possible to predefine project and asset. In that case their widgets
    will have passed preselected values and will be disabled.
    """


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
