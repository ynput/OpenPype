import os
import json
from Qt import QtWidgets, QtCore, QtGui
from pype.api import config
from .widgets import UnsavedChangesDialog
from . import lib
from avalon import io


class StudioWidget(QtWidgets.QWidget):
    is_overidable = False
    _is_overriden = False
    _is_group = False
    _any_parent_is_group = False

    def __init__(self, parent=None):
        super(StudioWidget, self).__init__(parent)

        self._ignore_value_changes = False

        self.input_fields = []

        scroll_widget = QtWidgets.QScrollArea(self)
        scroll_widget.setObjectName("GroupWidget")
        content_widget = QtWidgets.QWidget(scroll_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)
        content_layout.setSpacing(0)
        content_layout.setAlignment(QtCore.Qt.AlignTop)
        content_widget.setLayout(content_layout)

        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(content_widget)

        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget

        footer_widget = QtWidgets.QWidget()
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)

        save_btn = QtWidgets.QPushButton("Save")
        spacer_widget = QtWidgets.QWidget()
        footer_layout.addWidget(spacer_widget, 1)
        footer_layout.addWidget(save_btn, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addWidget(scroll_widget, 1)
        layout.addWidget(footer_widget, 0)

        save_btn.clicked.connect(self._save)

        self.reset()

    def any_parent_overriden(self):
        return False

    @property
    def is_overriden(self):
        return self._is_overriden

    @property
    def is_group(self):
        return self._is_group

    @property
    def any_parent_is_group(self):
        return self._any_parent_is_group

    @property
    def ignore_value_changes(self):
        return self._ignore_value_changes

    @ignore_value_changes.setter
    def ignore_value_changes(self, value):
        self._ignore_value_changes = value
        if value is False:
            self.hierarchical_style_update()

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def reset(self):
        if self.content_layout.count() != 0:
            for widget in self.input_fields:
                self.content_layout.removeWidget(widget)
                widget.deleteLater()
            self.input_fields.clear()

        self.schema = lib.gui_schema("studio_schema", "0_studio_gui_schema")
        self.keys = self.schema.get("keys", [])
        self.add_children_gui(self.schema)
        self._update_global_values()
        self.hierarchical_style_update()

    def _save(self):
        has_invalid = False
        for item in self.input_fields:
            if item.child_invalid:
                has_invalid = True

        if has_invalid:
            invalid_items = []
            for item in self.input_fields:
                invalid_items.extend(item.get_invalid())
            msg_box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                "Invalid input",
                "There is invalid value in one of inputs."
                " Please lead red color and fix them."
            )
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg_box.exec_()

            first_invalid_item = invalid_items[0]
            self.scroll_widget.ensureWidgetVisible(first_invalid_item)
            if first_invalid_item.isVisible():
                first_invalid_item.setFocus(True)
            return

        all_values = {}
        for item in self.input_fields:
            all_values.update(item.config_value())

        for key in reversed(self.keys):
            _all_values = {key: all_values}
            all_values = _all_values

        # Skip first key
        all_values = all_values["studio"]

        # Load studio data with metadata
        current_configurations = config.studio_configurations()

        keys_to_file = lib.file_keys_from_schema(self.schema)
        for key_sequence in keys_to_file:
            # Skip first key
            key_sequence = key_sequence[1:]
            subpath = "/".join(key_sequence) + ".json"
            origin_values = current_configurations
            for key in key_sequence:
                if not origin_values or key not in origin_values:
                    origin_values = {}
                    break
                origin_values = origin_values[key]

            if not origin_values:
                origin_values = {}

            new_values = all_values
            for key in key_sequence:
                new_values = new_values[key]
            origin_values.update(new_values)

            output_path = os.path.join(
                config.STUDIO_PRESETS_PATH, subpath
            )
            dirpath = os.path.dirname(output_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            print("Saving data to: ", output_path)
            with open(output_path, "w") as file_stream:
                json.dump(origin_values, file_stream, indent=4)

        self._update_global_values()

    def _update_global_values(self):
        values = {"studio": config.studio_configurations()}
        for input_field in self.input_fields:
            input_field.update_global_values(values)

        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        klass = lib.TypeToKlass.types.get(item_type)
        item = klass(child_configuration, self)
        self.input_fields.append(item)
        self.content_layout.addWidget(item)


class ProjectListView(QtWidgets.QListView):
    left_mouse_released_at = QtCore.Signal(QtCore.QModelIndex)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            index = self.indexAt(event.pos())
            self.left_mouse_released_at.emit(index)
        super(ProjectListView, self).mouseReleaseEvent(event)


class ProjectListWidget(QtWidgets.QWidget):
    default = "< Default >"
    project_changed = QtCore.Signal()

    def __init__(self, parent):
        self._parent = parent

        self.current_project = None

        super(ProjectListWidget, self).__init__(parent)
        self.setObjectName("ProjectListWidget")

        label_widget = QtWidgets.QLabel("Projects")

        project_list = ProjectListView(self)
        project_list.setModel(QtGui.QStandardItemModel())

        # Do not allow editing
        project_list.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        # Do not automatically handle selection
        project_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(3)
        layout.addWidget(label_widget, 0)
        layout.addWidget(project_list, 1)

        project_list.left_mouse_released_at.connect(self.on_item_clicked)

        self.project_list = project_list

        self.refresh()

    def on_item_clicked(self, new_index):
        new_project_name = new_index.data(QtCore.Qt.DisplayRole)
        if new_project_name is None:
            return

        if self.current_project == new_project_name:
            return

        save_changes = False
        change_project = False
        if self.validate_context_change():
            change_project = True

        else:
            dialog = UnsavedChangesDialog(self)
            result = dialog.exec_()
            if result == 1:
                save_changes = True
                change_project = True

            elif result == 2:
                change_project = True

        if save_changes:
            self._parent._save()

        if change_project:
            self.select_project(new_project_name)
            self.current_project = new_project_name
            self.project_changed.emit()
        else:
            self.select_project(self.current_project)

    def validate_context_change(self):
        # TODO add check if project can be changed (is modified)
        for item in self._parent.input_fields:
            is_modified = item.child_modified
            if is_modified:
                return False
        return True

    def project_name(self):
        if self.current_project == self.default:
            return None
        return self.current_project

    def select_project(self, project_name):
        model = self.project_list.model()
        found_items = model.findItems(project_name)
        if not found_items:
            found_items = model.findItems(self.default)

        index = model.indexFromItem(found_items[0])
        self.project_list.selectionModel().clear()
        self.project_list.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.SelectionFlag.SelectCurrent
        )

    def refresh(self):
        selected_project = None
        for index in self.project_list.selectedIndexes():
            selected_project = index.data(QtCore.Qt.DisplayRole)
            break

        model = self.project_list.model()
        model.clear()
        items = [self.default]
        io.install()
        for project_doc in tuple(io.projects()):
            items.append(project_doc["name"])

        for item in items:
            model.appendRow(QtGui.QStandardItem(item))

        self.select_project(selected_project)

        self.current_project = self.project_list.currentIndex().data(
            QtCore.Qt.DisplayRole
        )


class ProjectWidget(QtWidgets.QWidget):
    _is_overriden = False
    _is_group = False
    _any_parent_is_group = False

    def __init__(self, parent=None):
        super(ProjectWidget, self).__init__(parent)

        self.is_overidable = False
        self._ignore_value_changes = False
        self.project_name = None

        self.input_fields = []

        scroll_widget = QtWidgets.QScrollArea(self)
        scroll_widget.setObjectName("GroupWidget")
        content_widget = QtWidgets.QWidget(scroll_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)
        content_layout.setSpacing(0)
        content_layout.setAlignment(QtCore.Qt.AlignTop)
        content_widget.setLayout(content_layout)

        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(content_widget)

        project_list_widget = ProjectListWidget(self)
        content_layout.addWidget(project_list_widget)

        footer_widget = QtWidgets.QWidget()
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)

        save_btn = QtWidgets.QPushButton("Save")
        spacer_widget = QtWidgets.QWidget()
        footer_layout.addWidget(spacer_widget, 1)
        footer_layout.addWidget(save_btn, 0)

        configurations_widget = QtWidgets.QWidget()
        configurations_layout = QtWidgets.QVBoxLayout(configurations_widget)
        configurations_layout.setContentsMargins(5, 0, 5, 0)
        configurations_layout.setSpacing(0)

        configurations_layout.addWidget(scroll_widget, 1)
        configurations_layout.addWidget(footer_widget, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addWidget(project_list_widget, 0)
        layout.addWidget(configurations_widget, 1)

        save_btn.clicked.connect(self._save)
        project_list_widget.project_changed.connect(self._on_project_change)

        self.project_list_widget = project_list_widget
        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget

        self.reset()

    def any_parent_overriden(self):
        return False

    @property
    def is_overriden(self):
        return self._is_overriden

    @property
    def is_group(self):
        return self._is_group

    @property
    def any_parent_is_group(self):
        return self._any_parent_is_group

    @property
    def ignore_value_changes(self):
        return self._ignore_value_changes

    @ignore_value_changes.setter
    def ignore_value_changes(self, value):
        self._ignore_value_changes = value
        if value is False:
            self.hierarchical_style_update()

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def reset(self):
        self.schema = lib.gui_schema("projects_schema", "0_project_gui_schema")
        self.keys = self.schema.get("keys", [])
        self.add_children_gui(self.schema)
        self._update_global_values()
        self.hierarchical_style_update()

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        klass = lib.TypeToKlass.types.get(item_type)
        item = klass(child_configuration, self)
        self.input_fields.append(item)
        self.content_layout.addWidget(item)

    def _on_project_change(self):
        project_name = self.project_list_widget.project_name()
        if project_name is None:
            _overrides = lib.NOT_SET
            self.is_overidable = False
        else:
            _overrides = config.project_configurations_overrides(project_name)
            self.is_overidable = True

        overrides = {"project": lib.convert_overrides_to_gui_data(_overrides)}
        self.project_name = project_name
        self.ignore_value_changes = True
        for item in self.input_fields:
            item.apply_overrides(overrides)
        self.ignore_value_changes = False

    def _save(self):
        has_invalid = False
        for item in self.input_fields:
            if item.child_invalid:
                has_invalid = True

        if has_invalid:
            invalid_items = []
            for item in self.input_fields:
                invalid_items.extend(item.get_invalid())
            msg_box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                "Invalid input",
                "There is invalid value in one of inputs."
                " Please lead red color and fix them."
            )
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg_box.exec_()

            first_invalid_item = invalid_items[0]
            self.scroll_widget.ensureWidgetVisible(first_invalid_item)
            if first_invalid_item.isVisible():
                first_invalid_item.setFocus(True)
            return

        if self.project_name is None:
            self._save_defaults()
        else:
            self._save_overrides()

    def _save_overrides(self):
        _data = {}
        for item in self.input_fields:
            value, is_group = item.overrides()
            if value is not lib.NOT_SET:
                _data.update(value)
                if is_group:
                    raise Exception(
                        "Top item can't be overriden in Project widget."
                    )

        data = _data.get("project") or {}
        output_data = lib.convert_gui_data_to_overrides(data)

        overrides_json_path = config.path_to_project_overrides(
            self.project_name
        )
        dirpath = os.path.dirname(overrides_json_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        print("Saving data to: ", overrides_json_path)
        with open(overrides_json_path, "w") as file_stream:
            json.dump(output_data, file_stream, indent=4)

        self._on_project_change()

    def _save_defaults(self):
        output = {}
        for item in self.input_fields:
            output.update(item.config_value())

        for key in reversed(self.keys):
            _output = {key: output}
            output = _output

        all_values = {}
        for item in self.input_fields:
            all_values.update(item.config_value())

        for key in reversed(self.keys):
            _all_values = {key: all_values}
            all_values = _all_values

        # Skip first key
        all_values = all_values["project"]

        # Load studio data with metadata
        current_configurations = config.global_project_configurations()

        keys_to_file = lib.file_keys_from_schema(self.schema)
        for key_sequence in keys_to_file:
            # Skip first key
            key_sequence = key_sequence[1:]
            subpath = "/".join(key_sequence) + ".json"
            origin_values = current_configurations
            for key in key_sequence:
                if not origin_values or key not in origin_values:
                    origin_values = {}
                    break
                origin_values = origin_values[key]

            if not origin_values:
                origin_values = {}

            new_values = all_values
            for key in key_sequence:
                new_values = new_values[key]
            if isinstance(new_values, dict):
                origin_values.update(new_values)
            else:
                origin_values = new_values

            output_path = os.path.join(
                config.PROJECT_PRESETS_PATH, subpath
            )
            dirpath = os.path.dirname(output_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            print("Saving data to: ", output_path)
            with open(output_path, "w") as file_stream:
                json.dump(origin_values, file_stream, indent=4)

        self._update_global_values()

    def _update_global_values(self):
        values = {"project": config.global_project_configurations()}
        for input_field in self.input_fields:
            input_field.update_global_values(values)

        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
