import os
import json
from Qt import QtWidgets, QtCore, QtGui
from . import config
from .widgets import UnsavedChangesDialog
from .lib import NOT_SET, METADATA_KEY
from avalon import io


class TypeToKlass:
    types = {}


class PypeConfigurationWidget:
    default_state = ""

    def config_value(self):
        raise NotImplementedError(
            "Method `config_value` is not implemented for `{}`.".format(
                self.__class__.__name__
            )
        )

    def value_from_values(self, values, keys=None):
        if not values:
            return NOT_SET

        if keys is None:
            keys = self.keys

        value = values
        for key in keys:
            if not isinstance(value, dict):
                raise TypeError(
                    "Expected dictionary got {}.".format(str(type(value)))
                )

            if key not in value:
                return NOT_SET
            value = value[key]
        return value

    def style_state(self, is_overriden, is_modified):
        items = []
        if is_overriden:
            items.append("overriden")
        if is_modified:
            items.append("modified")
        return "-".join(items) or self.default_state

    def add_children_gui(self, child_configuration, values):
        raise NotImplementedError((
            "Method `add_children_gui` is not implemented for `{}`."
        ).format(self.__class__.__name__))


class StudioWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    is_overidable = False
    is_overriden = False
    is_group = False
    any_parent_is_group = False
    ignore_value_changes = False

    def __init__(self, parent=None):
        super(StudioWidget, self).__init__(parent)

        self.input_fields = []

        scroll_widget = QtWidgets.QScrollArea(self)
        content_widget = QtWidgets.QWidget(scroll_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)
        content_layout.setSpacing(0)
        content_layout.setAlignment(QtCore.Qt.AlignTop)
        content_widget.setLayout(content_layout)

        # scroll_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # scroll_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addWidget(scroll_widget, 1)
        layout.addWidget(footer_widget, 0)

        save_btn.clicked.connect(self._save)

        self.reset()

    def reset(self):
        if self.content_layout.count() != 0:
            for widget in self.input_fields:
                self.content_layout.removeWidget(widget)
                widget.deleteLater()
            self.input_fields.clear()

        values = {"studio": config.studio_presets()}
        schema = config.gui_schema("studio_schema", "studio_gui_schema")
        self.keys = schema.get("keys", [])
        self.add_children_gui(schema, values)
        self.schema = schema

    def _save(self):
        all_values = {}
        for item in self.input_fields:
            all_values.update(item.config_value())

        for key in reversed(self.keys):
            _all_values = {key: all_values}
            all_values = _all_values

        # Skip first key
        all_values = all_values["studio"]

        # Load studio data with metadata
        current_presets = config.studio_presets()

        keys_to_file = config.file_keys_from_schema(self.schema)
        for key_sequence in keys_to_file:
            # Skip first key
            key_sequence = key_sequence[1:]
            subpath = "/".join(key_sequence) + ".json"
            origin_values = current_presets
            for key in key_sequence:
                if key not in origin_values:
                    origin_values = {}
                    break
                origin_values = origin_values[key]

            new_values = all_values
            for key in key_sequence:
                new_values = new_values[key]
            origin_values.update(new_values)

            output_path = os.path.join(
                config.studio_presets_path, subpath
            )
            dirpath = os.path.dirname(output_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            with open(output_path, "w") as file_stream:
                json.dump(origin_values, file_stream, indent=4)

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)
        item = klass(
            child_configuration, values, self.keys, self
        )
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


class ProjectWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    is_overriden = False
    is_group = False
    any_parent_is_group = False

    def __init__(self, parent=None):
        super(ProjectWidget, self).__init__(parent)

        self.is_overidable = False
        self.ignore_value_changes = False
        self.project_name = None

        self.input_fields = []

        scroll_widget = QtWidgets.QScrollArea(self)
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

        presets_widget = QtWidgets.QWidget()
        presets_layout = QtWidgets.QVBoxLayout(presets_widget)
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(0)

        presets_layout.addWidget(scroll_widget, 1)
        presets_layout.addWidget(footer_widget, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addWidget(project_list_widget, 0)
        layout.addWidget(presets_widget, 1)

        save_btn.clicked.connect(self._save)
        project_list_widget.project_changed.connect(self._on_project_change)

        self.project_list_widget = project_list_widget
        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget

        self.reset()

    def reset(self):
        values = config.global_project_presets()
        schema = config.gui_schema("projects_schema", "project_gui_schema")
        self.keys = schema.get("keys", [])
        self.add_children_gui(schema, values)

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        item = klass(
            child_configuration, values, self.keys, self
        )
        self.input_fields.append(item)
        self.content_layout.addWidget(item)

    def _on_project_change(self):
        project_name = self.project_list_widget.project_name()
        if project_name is None:
            overrides = None
            self.is_overidable = False
        else:
            overrides = config.project_preset_overrides(project_name)
            self.is_overidable = True

        self.project_name = project_name
        self.ignore_value_changes = True
        for item in self.input_fields:
            item.apply_overrides(overrides)
        self.ignore_value_changes = False

    def _save(self):
        if self.project_name is None:
            self._save_defaults()
        else:
            self._save_overrides()

    def _save_overrides(self):
        data = {}
        groups = []
        for item in self.input_fields:
            value, is_group = item.overrides()
            if value is not NOT_SET:
                data.update(value)

                if is_group:
                    groups.extend(value.keys())

        if groups:
            data[METADATA_KEY] = {"groups": groups}
        output = convert_to_override(data)
        print(json.dumps(output, indent=4))

    def _save_defaults(self):
        output = {}
        for item in self.input_fields:
            output.update(item.config_value())

        for key in reversed(self.keys):
            _output = {key: output}
            output = _output

        print(json.dumps(output, indent=4))
        return

        # TODO check implementation copied from studio
        all_values = {}
        for item in self.input_fields:
            all_values.update(item.config_value())

        for key in reversed(self.keys):
            _all_values = {key: all_values}
            all_values = _all_values

        # Skip first key
        all_values = all_values["studio"]

        # Load studio data with metadata
        current_presets = config.studio_presets()

        keys_to_file = config.file_keys_from_schema(self.schema)
        for key_sequence in keys_to_file:
            # Skip first key
            key_sequence = key_sequence[1:]
            subpath = "/".join(key_sequence) + ".json"
            origin_values = current_presets
            for key in key_sequence:
                if key not in origin_values:
                    origin_values = {}
                    break
                origin_values = origin_values[key]

            new_values = all_values
            for key in key_sequence:
                new_values = new_values[key]
            origin_values.update(new_values)

            output_path = os.path.join(
                config.studio_presets_path, subpath
            )
            dirpath = os.path.dirname(output_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            with open(output_path, "w") as file_stream:
                json.dump(origin_values, file_stream, indent=4)
