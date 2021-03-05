import os
import sys

from avalon import style
from Qt import QtCore, QtGui, QtWidgets
from pype.api import Logger, resources
import pype.version


class PypeInfoWidget(QtWidgets.QWidget):
    not_allowed = "N/A"

    def __init__(self, parent=None):
        super(PypeInfoWidget, self).__init__(parent)

        self.setStyleSheet(style.load_stylesheet())

        icon = QtGui.QIcon(resources.pype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("Pype info")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self._create_pype_info_widget())

    def _create_pype_info_widget(self):
        """Create widget with information about pype application."""
        pype_root = os.environ["PYPE_ROOT"]
        if getattr(sys, "frozen", False):
            version_end = "build"
            executable_path = sys.executable
        else:
            version_end = "code"
            executable_path = os.path.join(pype_root, "start.py")
        version_value = "{} ({})".format(
            pype.version.__version__, version_end
        )

        lable_value = [
            # Pype version
            ("Pype version:", version_value),
            ("Pype executable:", executable_path),
            ("Pype location:", pype_root),

            # Mongo URL
            ("Pype Mongo URL:", os.environ.get("PYPE_MONGO"))
        ]

        info_widget = QtWidgets.QWidget(self)
        info_layout = QtWidgets.QGridLayout(info_widget)

        title_label = QtWidgets.QLabel(info_widget)
        title_label.setText("Application information")
        title_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(title_label, 0, 0, 1, 2)

        for label, value in lable_value:
            row = info_layout.rowCount()
            info_layout.addWidget(
                QtWidgets.QLabel(label), row, 0, 1, 1
            )
            value_label = QtWidgets.QLabel(value or self.not_allowed)
            info_layout.addWidget(
                value_label, row, 1, 1, 1
            )
        return info_widget

    def showEvent(self, event):
        """Center widget to center of desktop on show."""
        result = super(PypeInfoWidget, self).showEvent(event)
        screen_center = (
            QtWidgets.QApplication.desktop().availableGeometry(self).center()
        )
        self.move(
            screen_center.x() - (self.width() / 2),
            screen_center.y() - (self.height() / 2)
        )
        return result
