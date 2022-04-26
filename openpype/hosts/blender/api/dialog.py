"""dialog to enhance the openpype windows"""

import typing

import openpype
from Qt.QtWidgets import (
    QMainWindow,
    QApplication,
    QMessageBox,
)


def find_window(type) -> typing.Union[QMainWindow, None]:
    # Global function to find the (open) QMainWindow in application
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, type):
            return widget
    return None


def use_selection_behaviour_dialog() -> bool:
    window = find_window(openpype.tools.creator.window.CreatorWindow)
    result = QMessageBox.question(
        window,
        "MessageBox",
        "You enabled use selected but no any object is selected. "
        "All objects from the scene will be moved under the created instance,"
        " do you want to continue?",
        (QMessageBox.Yes | QMessageBox.No),
        QMessageBox.No,
    )
    return result == QMessageBox.Yes


def container_already_exist_dialog():
    window = find_window(openpype.tools.creator.window.CreatorWindow)
    msgBox = QMessageBox(window)

    msgBox.setText("This instance already exists.")
    msgBox.exec()
