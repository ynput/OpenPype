import os
import json
import collections

from Qt import QtCore, QtGui, QtWidgets

from openpype import style
from openpype.api import resources
from openpype.settings.lib import get_local_settings
from openpype.lib.pype_info import (
    get_all_current_info,
    get_openpype_info,
    get_workstation_info,
    extract_pype_info_to_file
)

IS_MAIN_ROLE = QtCore.Qt.UserRole


class EnvironmentValueDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        edit_widget = QtWidgets.QLineEdit(parent)
        edit_widget.setReadOnly(True)
        return edit_widget


class EnvironmentsView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super(EnvironmentsView, self).__init__(parent)

        self._scroll_enabled = False

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
            key_item.setData(True, IS_MAIN_ROLE)
            keys.append(key_item)

            value = env[key]
            value_item = QtGui.QStandardItem(value)
            value_item.setData(True, IS_MAIN_ROLE)
            values.append(value_item)

            value_parts = [
                part
                for part in value.split(os.pathsep) if part
            ]
            if len(value_parts) < 2:
                continue

            sub_parts = []
            for part_value in value_parts:
                part_item = QtGui.QStandardItem(part_value)
                part_item.setData(False, IS_MAIN_ROLE)
                sub_parts.append(part_item)
            key_item.appendRows(sub_parts)

        model.appendColumn(keys)
        model.appendColumn(values)
        model.setHorizontalHeaderLabels(["Key", "Value"])

        self.setModel(model)
        # self.setIndentation(0)
        delegate = EnvironmentValueDelegate(self)
        self.setItemDelegate(delegate)
        self.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        self.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)

    def get_selection_as_dict(self):
        indexes = self.selectionModel().selectedIndexes()

        main_mapping = collections.defaultdict(dict)
        for index in indexes:
            is_main = index.data(IS_MAIN_ROLE)
            if not is_main:
                continue
            row = index.row()
            value = index.data(QtCore.Qt.DisplayRole)
            if index.column() == 0:
                key = "key"
            else:
                key = "value"
            main_mapping[row][key] = value

        result = {}
        for item in main_mapping.values():
            result[item["key"]] = item["value"]
        return result

    def keyPressEvent(self, event):
        if (
            event.type() == QtGui.QKeyEvent.KeyPress
            and event.matches(QtGui.QKeySequence.Copy)
        ):
            selected_data = self.get_selection_as_dict()
            selected_str = json.dumps(selected_data, indent=4)

            mime_data = QtCore.QMimeData()
            mime_data.setText(selected_str)
            QtWidgets.QApplication.instance().clipboard().setMimeData(
                mime_data
            )
            event.accept()
        else:
            return super(EnvironmentsView, self).keyPressEvent(event)

    def set_scroll_enabled(self, value):
        self._scroll_enabled = value

    def wheelEvent(self, event):
        if not self._scroll_enabled:
            event.ignore()
            return
        return super(EnvironmentsView, self).wheelEvent(event)


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

        top_part_layout = QtWidgets.QHBoxLayout(top_part)
        top_part_layout.setContentsMargins(0, 0, 0, 5)
        top_part_layout.addWidget(button_toggle)
        top_part_layout.addWidget(label_widget)
        top_part_layout.addStretch(1)

        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
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
    _resized = QtCore.Signal()

    def __init__(self, parent=None):
        super(PypeInfoWidget, self).__init__(parent)

        self._scroll_at_bottom = False

        self.setStyleSheet(style.load_stylesheet())

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("OpenPype info")

        scroll_area = QtWidgets.QScrollArea(self)
        info_widget = PypeInfoSubWidget(scroll_area)

        scroll_area.setWidget(info_widget)
        scroll_area.setWidgetResizable(True)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(scroll_area, 1)
        main_layout.addWidget(self._create_btns_section(), 0)

        scroll_area.verticalScrollBar().valueChanged.connect(
            self._on_area_scroll
        )
        self._resized.connect(self._on_resize)
        self.resize(740, 540)

        self.scroll_area = scroll_area
        self.info_widget = info_widget

    def _on_area_scroll(self, value):
        vertical_bar = self.scroll_area.verticalScrollBar()
        self._scroll_at_bottom = vertical_bar.maximum() == vertical_bar.value()
        self.info_widget.set_scroll_enabled(self._scroll_at_bottom)

    def _on_resize(self):
        if not self._scroll_at_bottom:
            return
        vertical_bar = self.scroll_area.verticalScrollBar()
        vertical_bar.setValue(vertical_bar.maximum())

    def resizeEvent(self, event):
        super(PypeInfoWidget, self).resizeEvent(event)
        self._resized.emit()
        self.info_widget.set_content_height(
            self.scroll_area.height()
        )

    def showEvent(self, event):
        super(PypeInfoWidget, self).showEvent(event)
        self.info_widget.set_content_height(
            self.scroll_area.height()
        )

    def _create_btns_section(self):
        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)

        copy_to_clipboard_btn = QtWidgets.QPushButton(
            "Copy to clipboard", btns_widget
        )
        export_to_file_btn = QtWidgets.QPushButton(
            "Export", btns_widget
        )
        btns_layout.addWidget(QtWidgets.QWidget(btns_widget), 1)
        btns_layout.addWidget(copy_to_clipboard_btn)
        btns_layout.addWidget(export_to_file_btn)

        copy_to_clipboard_btn.clicked.connect(self._on_copy_to_clipboard)
        export_to_file_btn.clicked.connect(self._on_export_to_file)

        return btns_widget

    def _on_export_to_file(self):
        dst_dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choose directory",
            os.path.expanduser("~"),
            QtWidgets.QFileDialog.ShowDirsOnly
        )
        if not dst_dir_path or not os.path.exists(dst_dir_path):
            return

        filepath = extract_pype_info_to_file(dst_dir_path)
        title = "Extraction done"
        message = "Extraction is done. Destination filepath is \"{}\"".format(
            filepath.replace("\\", "/")
        )
        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.NoIcon)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.exec_()

    def _on_copy_to_clipboard(self):
        all_data = get_all_current_info()
        all_data_str = json.dumps(all_data, indent=4)

        mime_data = QtCore.QMimeData()
        mime_data.setText(all_data_str)
        QtWidgets.QApplication.instance().clipboard().setMimeData(
            mime_data
        )


class PypeInfoSubWidget(QtWidgets.QWidget):
    not_applicable = "N/A"

    def __init__(self, parent=None):
        super(PypeInfoSubWidget, self).__init__(parent)

        self.env_view = None

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.addWidget(self._create_openpype_info_widget(), 0)
        main_layout.addWidget(self._create_separator(), 0)
        main_layout.addWidget(self._create_workstation_widget(), 0)
        main_layout.addWidget(self._create_separator(), 0)
        main_layout.addWidget(self._create_local_settings_widget(), 0)
        main_layout.addWidget(self._create_separator(), 0)
        main_layout.addWidget(self._create_environ_widget(), 1)

    def set_content_height(self, height):
        if self.env_view:
            self.env_view.setMinimumHeight(height)

    def set_scroll_enabled(self, value):
        if self.env_view:
            self.env_view.set_scroll_enabled(value)

    def _create_separator(self):
        separator_widget = QtWidgets.QWidget(self)
        separator_widget.setObjectName("Separator")
        separator_widget.setMinimumHeight(2)
        separator_widget.setMaximumHeight(2)
        return separator_widget

    def _create_workstation_widget(self):
        key_label_mapping = {
            "system_name": "System:",
            "local_id": "Local ID:",
            "username": "Username:",
            "hostname": "Hostname:",
            "hostip": "Host IP:"
        }
        keys_order = [
            "system_name",
            "local_id",
            "username",
            "hostname",
            "hostip"
        ]
        workstation_info = get_workstation_info()
        for key in workstation_info.keys():
            if key not in keys_order:
                keys_order.append(key)

        wokstation_info_widget = CollapsibleWidget("Workstation info", self)

        info_widget = QtWidgets.QWidget(self)
        info_layout = QtWidgets.QGridLayout(info_widget)
        # Add spacer to 3rd column
        info_layout.addWidget(QtWidgets.QWidget(info_widget), 0, 2)
        info_layout.setColumnStretch(2, 1)

        for key in keys_order:
            if key not in workstation_info:
                continue

            label = key_label_mapping.get(key, key)
            value = workstation_info[key]
            row = info_layout.rowCount()
            info_layout.addWidget(
                QtWidgets.QLabel(label), row, 0, 1, 1
            )
            value_label = QtWidgets.QLabel(value)
            value_label.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            info_layout.addWidget(
                value_label, row, 1, 1, 1
            )

        wokstation_info_widget.set_content_widget(info_widget)
        wokstation_info_widget.toggle_content()

        return wokstation_info_widget

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
        env_view.setMinimumHeight(300)
        env_widget.set_content_widget(env_view)

        self.env_view = env_view

        return env_widget

    def _create_openpype_info_widget(self):
        """Create widget with information about OpenPype application."""

        # Get pype info data
        pype_info = get_openpype_info()
        # Modify version key/values
        version_value = "{} ({})".format(
            pype_info.pop("version", self.not_applicable),
            pype_info.pop("version_type", self.not_applicable)
        )
        pype_info["version_value"] = version_value
        # Prepare label mapping
        key_label_mapping = {
            "version_value": "Running version:",
            "build_verison": "Build version:",
            "executable": "OpenPype executable:",
            "pype_root": "OpenPype location:",
            "mongo_url": "OpenPype Mongo URL:"
        }
        # Prepare keys order
        keys_order = [
            "version_value",
            "build_verison",
            "executable",
            "pype_root",
            "mongo_url"
        ]
        for key in pype_info.keys():
            if key not in keys_order:
                keys_order.append(key)

        # Create widgets
        info_widget = QtWidgets.QWidget(self)
        info_layout = QtWidgets.QGridLayout(info_widget)
        # Add spacer to 3rd column
        info_layout.addWidget(QtWidgets.QWidget(info_widget), 0, 2)
        info_layout.setColumnStretch(2, 1)

        title_label = QtWidgets.QLabel(info_widget)
        title_label.setText("Application information")
        title_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(title_label, 0, 0, 1, 2)

        for key in keys_order:
            if key not in pype_info:
                continue
            value = pype_info[key]
            label = key_label_mapping.get(key, key)
            row = info_layout.rowCount()
            info_layout.addWidget(
                QtWidgets.QLabel(label), row, 0, 1, 1
            )
            value_label = QtWidgets.QLabel(value)
            value_label.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            info_layout.addWidget(
                value_label, row, 1, 1, 1
            )
        return info_widget
