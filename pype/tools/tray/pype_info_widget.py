import os
import sys
import json
import collections

from avalon import style
from Qt import QtCore, QtGui, QtWidgets
from pype.api import resources
import pype.version
from pype.settings.lib import get_local_settings
from pype.lib.pype_info import (
    get_pype_info,
    get_workstation_info,
    extract_pype_info_to_file
)


class EnvironmentValueDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        edit_widget = QtWidgets.QLineEdit(parent)
        edit_widget.setReadOnly(True)
        return edit_widget


class EnvironmentsView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super(EnvironmentsView, self).__init__(parent)

        model = QtGui.QStandardItemModel()

        env = os.environ.copy()
        keys = []
        values = []
        for key in sorted(env.keys()):
            key_item = QtGui.QStandardItem(key)
            key_item.setFlags(
                QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsEnabled
            )
            keys.append(key_item)
            values.append(QtGui.QStandardItem(env[key]))

        model.appendColumn(keys)
        model.appendColumn(values)
        model.setHorizontalHeaderLabels(["Key", "Value"])

        self.setModel(model)
        self.setIndentation(0)
        delegate = EnvironmentValueDelegate(self)
        self.setItemDelegateForColumn(1, delegate)
        self.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        self.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)

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


class ClickableWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ClickableWidget, self).mouseReleaseEvent(event)


class CollapsibleWidget(QtWidgets.QWidget):
    def __init__(self, label, parent):
        super(CollapsibleWidget, self).__init__(parent)

        self.content_widget = None

        top_part = ClickableWidget(parent=self)

        button_size = QtCore.QSize(5, 5)
        button_toggle = QtWidgets.QToolButton(parent=top_part)
        button_toggle.setIconSize(button_size)
        button_toggle.setArrowType(QtCore.Qt.RightArrow)
        button_toggle.setCheckable(True)
        button_toggle.setChecked(False)

        label_widget = QtWidgets.QLabel(label, parent=top_part)
        spacer_widget = QtWidgets.QWidget(top_part)

        top_part_layout = QtWidgets.QHBoxLayout(top_part)
        top_part_layout.setContentsMargins(0, 0, 0, 5)
        top_part_layout.addWidget(button_toggle)
        top_part_layout.addWidget(label_widget)
        top_part_layout.addWidget(spacer_widget, 1)

        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        spacer_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.button_toggle = button_toggle
        self.label_widget = label_widget

        top_part.clicked.connect(self._top_part_clicked)
        self.button_toggle.clicked.connect(self._btn_clicked)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.addWidget(top_part)

        self.main_layout = main_layout

    def set_content_widget(self, content_widget):
        content_widget.setVisible(self.button_toggle.isChecked())
        self.main_layout.addWidget(content_widget)
        self.content_widget = content_widget

    def _btn_clicked(self):
        self.toggle_content(self.button_toggle.isChecked())

    def _top_part_clicked(self):
        self.toggle_content()

    def toggle_content(self, *args):
        if len(args) > 0:
            checked = args[0]
        else:
            checked = not self.button_toggle.isChecked()
        arrow_type = QtCore.Qt.RightArrow
        if checked:
            arrow_type = QtCore.Qt.DownArrow
        self.button_toggle.setChecked(checked)
        self.button_toggle.setArrowType(arrow_type)
        if self.content_widget:
            self.content_widget.setVisible(checked)
        self.parent().updateGeometry()

    def resizeEvent(self, event):
        super(CollapsibleWidget, self).resizeEvent(event)
        if self.content_widget:
            self.content_widget.updateGeometry()


class PypeInfoWidget(QtWidgets.QWidget):
    not_allowed = "N/A"

    def __init__(self, parent=None):
        super(PypeInfoWidget, self).__init__(parent)

        self.setStyleSheet(style.load_stylesheet())

        icon = QtGui.QIcon(resources.pype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("Pype info")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.addWidget(self._create_pype_info_widget(), 0)
        main_layout.addWidget(self._create_separator(), 0)
        main_layout.addWidget(self._create_local_settings_widget(), 0)
        main_layout.addWidget(self._create_separator(), 0)
        main_layout.addWidget(self._create_environ_widget(), 1)

    def _create_separator(self):
        separator_widget = QtWidgets.QWidget(self)
        separator_widget.setStyleSheet("background: #222222;")
        separator_widget.setMinimumHeight(2)
        separator_widget.setMaximumHeight(2)
        return separator_widget

    def _create_local_settings_widget(self):
        local_settings = get_local_settings()

        local_settings_widget = CollapsibleWidget("Local settings", self)

        settings_input = QtWidgets.QPlainTextEdit(local_settings_widget)
        settings_input.setReadOnly(True)
        settings_input.setPlainText(json.dumps(local_settings, indent=4))

        local_settings_widget.set_content_widget(settings_input)

        return local_settings_widget

    def _create_environ_widget(self):
        env_widget = CollapsibleWidget("Environments", self)

        env_view = EnvironmentsView(env_widget)

        env_widget.set_content_widget(env_view)

        return env_widget

    def _create_pype_info_widget(self):
        """Create widget with information about pype application."""

        pype_info = get_pype_info()
        version_value = "{} ({})".format(
            pype_info["version"],
            pype_info["version_type"]
        )
        lable_value = [
            # Pype version
            ("Pype version:", version_value),
            ("Pype executable:", pype_info["executable"]),
            ("Pype location:", pype_info["pype_root"]),

            # Mongo URL
            ("Pype Mongo URL:", pype_info["mongo_url"])
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
