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
    is_selection_behavior_accept = True
    window = find_window(openpype.tools.creator.window.CreatorWindow)

    ret = QMessageBox.question(
        window,
        "MessageBox",
        "You enabled use selected but no any object is selected. "
        "All objects from the scene will be moved under the created instance,"
        " do you want to continue?",
        (QMessageBox.Yes | QMessageBox.No),
        QMessageBox.No,
    )
    if ret == QMessageBox.No:
        is_selection_behavior_accept = False
    if ret == QMessageBox.Yes:
        is_selection_behavior_accept = True
    return is_selection_behavior_accept
