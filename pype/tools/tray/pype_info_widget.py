import os
import sys
import json
import collections

from avalon import style
from Qt import QtCore, QtGui, QtWidgets
from pype.api import resources
import pype.version


class EnvironmentsView(QtWidgets.QTreeView):
    def __init__(self, model, parent=None):
        super(EnvironmentsView, self).__init__(parent)
        self.setModel(model)
        self.setIndentation(0)
        self.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        self.setSelectionMode(QtWidgets.QTreeView.MultiSelection)

    def get_all_as_dict(self):
        pass

    def get_selection_as_dict(self):
        indexes = self.selectionModel().selectedIndexes()
        mapping = collections.defaultdict(dict)
        for index in indexes:
            row = index.row()
            value = index.data(QtCore.Qt.DisplayRole)
            if index.column() == 0:
                key = "key"
            else:
                key = "value"
            mapping[row][key] = value
        result = {}
        for item in mapping.values():
            result[item["key"]] = item["value"]
        return result

    def keyPressEvent(self, event):
        if (
            event.type() == QtGui.QKeyEvent.KeyPress
            and event.matches(QtGui.QKeySequence.Copy)
        ):
            selected_dict = self.get_selection_as_dict()
            selected_str = json.dumps(selected_dict, indent=4)

            mime_data = QtCore.QMimeData()
            mime_data.setText(selected_str)
            QtWidgets.QApplication.instance().clipboard().setMimeData(
                mime_data
            )
            event.accept()
        else:
            return super(EnvironmentsView, self).keyPressEvent(event)


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
        main_layout.addWidget(self._create_environ_widget())

    def _create_environ_widget(self):
        env_widget = QtWidgets.QWidget(self)

        env_label_widget = QtWidgets.QLabel("Environments", env_widget)
        env_label_widget.setStyleSheet("font-weight: bold;")

        env_model = QtGui.QStandardItemModel()

        env = os.environ.copy()
        keys = []
        values = []
        for key in sorted(env.keys()):
            keys.append(QtGui.QStandardItem(key))
            values.append(QtGui.QStandardItem(env[key]))

        env_model.appendColumn(keys)
        env_model.appendColumn(values)
        env_model.setHorizontalHeaderLabels(["Key", "Value"])

        env_view = EnvironmentsView(env_model, env_widget)

        env_layout = QtWidgets.QVBoxLayout(env_widget)
        env_layout.addWidget(env_label_widget)
        env_layout.addWidget(env_view)

        return env_widget

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
        # Add spacer to 3rd column
        info_layout.addWidget(QtWidgets.QWidget(info_widget), 0, 2)
        info_layout.setColumnStretch(2, 1)

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
            value_label.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
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
