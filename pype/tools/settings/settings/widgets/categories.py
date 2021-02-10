import os
import json
from enum import Enum
from Qt import QtWidgets, QtCore, QtGui
from pype.settings.constants import (
    PROJECT_SETTINGS_KEY,
    PROJECT_ANATOMY_KEY
)
from pype.settings.entities import (
    base_entity,
    GUIEntity,
    DictImmutableKeysEntity,
    DictMutableKeysEntity,
    ListEntity,
    PathEntity,
    ListStrictEntity,

    NumberEntity,
    BoolEntity,
    EnumEntity,
    TextEntity,
    PathInput,
    RawJsonEntity,

    DefaultsNotDefined
)

from pype.settings.lib import (
    DEFAULTS_DIR,

    reset_default_settings,
    get_default_settings,

    get_studio_project_settings_overrides,
    get_studio_project_anatomy_overrides,

    get_project_settings_overrides,
    get_project_anatomy_overrides,

    save_project_settings,
    save_project_anatomy,

    get_system_settings
)
from .widgets import UnsavedChangesDialog
from . import lib

from .base import GUIWidget
from .list_item_widget import ListWidget
from .dict_mutable_widget import DictMutableKeysWidget
from .item_widgets import (
    BoolWidget,
    DictImmutableKeysWidget,
    TextWidget,
    NumberWidget,
    RawJsonWidget,
    EnumeratorWidget,
    PathWidget,
    PathInputWidget
)
from avalon.mongodb import (
    AvalonMongoConnection,
    AvalonMongoDB
)
from avalon.vendor import qtawesome


class CategoryState(Enum):
    Idle = object()
    Working = object()


class SettingsCategoryWidget(QtWidgets.QWidget):
    schema_category = None
    initial_schema_name = None

    state_changed = QtCore.Signal()
    saved = QtCore.Signal(QtWidgets.QWidget)

    def __init__(self, user_role, parent=None):
        super(SettingsCategoryWidget, self).__init__(parent)

        self.user_role = user_role

        self._state = CategoryState.Idle

        self.initialize_attributes()
        self.create_ui()

    @staticmethod
    def create_ui_for_entity(entity, entity_widget):
        if isinstance(entity, GUIEntity):
            return GUIWidget(entity, entity_widget)

        elif isinstance(entity, DictImmutableKeysEntity):
            return DictImmutableKeysWidget(entity, entity_widget)

        elif isinstance(entity, BoolEntity):
            return BoolWidget(entity, entity_widget)

        elif isinstance(entity, TextEntity):
            return TextWidget(entity, entity_widget)

        elif isinstance(entity, NumberEntity):
            return NumberWidget(entity, entity_widget)

        elif isinstance(entity, RawJsonEntity):
            return RawJsonWidget(entity, entity_widget)

        elif isinstance(entity, EnumEntity):
            return EnumeratorWidget(entity, entity_widget)

        elif isinstance(entity, PathEntity):
            return PathWidget(entity, entity_widget)

        elif isinstance(entity, PathInput):
            return PathInputWidget(entity, entity_widget)

        elif isinstance(entity, ListEntity):
            return ListWidget(entity, entity_widget)

        elif isinstance(entity, DictMutableKeysEntity):
            return DictMutableKeysWidget(entity, entity_widget)

        elif isinstance(entity, ListStrictEntity):
            pass

        label = "<{}>: {} ({})".format(
            entity.__class__.__name__, entity.path, entity.value
        )
        raise TypeError("Unknown type: ".format(label))

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self.set_state(value)

    def set_state(self, state):
        if self._state == state:
            return

        self._state = state
        self.state_changed.emit()

        # Process events so emitted signal is processed
        app = QtWidgets.QApplication.instance()
        if app:
            app.processEvents()

    def initialize_attributes(self):
        self._hide_studio_overrides = False
        self._ignore_value_changes = False

        self.keys = []
        self.input_fields = []
        self.schema = None
        self.main_schema_key = None

        # Required attributes for items
        self.is_overidable = False
        self._has_studio_override = False
        self._is_overriden = False
        self._as_widget = False
        self._is_group = False
        self._any_parent_as_widget = False
        self._any_parent_is_group = False
        self.has_studio_override = self._has_studio_override
        self.is_overriden = self._is_overriden
        self.as_widget = self._as_widget
        self.is_group = self._as_widget
        self.any_parent_as_widget = self._any_parent_as_widget
        self.any_parent_is_group = self._any_parent_is_group

    def create_ui(self):
        scroll_widget = QtWidgets.QScrollArea(self)
        scroll_widget.setObjectName("GroupWidget")
        content_widget = QtWidgets.QWidget(scroll_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)
        content_layout.setSpacing(0)
        content_layout.setAlignment(QtCore.Qt.AlignTop)

        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(content_widget)

        configurations_widget = QtWidgets.QWidget(self)

        footer_widget = QtWidgets.QWidget(configurations_widget)
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)

        if self.user_role == "developer":
            self._add_developer_ui(footer_layout)

        save_btn = QtWidgets.QPushButton("Save")
        spacer_widget = QtWidgets.QWidget()
        footer_layout.addWidget(spacer_widget, 1)
        footer_layout.addWidget(save_btn, 0)

        configurations_layout = QtWidgets.QVBoxLayout(configurations_widget)
        configurations_layout.setContentsMargins(0, 0, 0, 0)
        configurations_layout.setSpacing(0)

        configurations_layout.addWidget(scroll_widget, 1)
        configurations_layout.addWidget(footer_widget, 0)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(configurations_widget, 1)

        save_btn.clicked.connect(self._save)

        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget
        self.configurations_widget = configurations_widget
        self.main_layout = main_layout

        self.ui_tweaks()

    def ui_tweaks(self):
        return

    def _add_developer_ui(self, footer_layout):
        save_as_default_btn = QtWidgets.QPushButton("Save as Default")

        refresh_icon = qtawesome.icon("fa.refresh", color="white")
        refresh_button = QtWidgets.QPushButton()
        refresh_button.setIcon(refresh_icon)

        hide_studio_overrides = QtWidgets.QCheckBox()
        hide_studio_overrides.setChecked(self._hide_studio_overrides)

        hide_studio_overrides_widget = QtWidgets.QWidget()
        hide_studio_overrides_layout = QtWidgets.QHBoxLayout(
            hide_studio_overrides_widget
        )
        _label_widget = QtWidgets.QLabel(
            "Hide studio overrides", hide_studio_overrides_widget
        )
        hide_studio_overrides_layout.addWidget(_label_widget)
        hide_studio_overrides_layout.addWidget(hide_studio_overrides)

        footer_layout.addWidget(save_as_default_btn, 0)
        footer_layout.addWidget(refresh_button, 0)
        footer_layout.addWidget(hide_studio_overrides_widget, 0)

        save_as_default_btn.clicked.connect(self._save_as_defaults)
        refresh_button.clicked.connect(self._on_refresh)
        hide_studio_overrides.stateChanged.connect(
            self._on_hide_studio_overrides
        )

    def save(self):
        """Save procedure."""
        raise NotImplementedError("Method `save` is not implemented.")

    def defaults_dir(self):
        """Path to defaults folder."""
        raise NotImplementedError("Method `defaults_dir` is not implemented.")

    def update_values(self):
        """Procedure of update values of items on context change or reset."""
        raise NotImplementedError("Method `update_values` is not implemented.")

    def validate_defaults_to_save(self, value):
        raise NotImplementedError(
            "Method `validate_defaults_to_save` not implemented."
        )

    def any_parent_overriden(self):
        return False

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
        self.set_state(CategoryState.Working)

        reset_default_settings()

        self.keys.clear()
        self.input_fields.clear()
        while self.content_layout.count() != 0:
            widget = self.content_layout.itemAt(0).widget()
            widget.setVisible(False)
            self.content_layout.removeWidget(widget)
            widget.deleteLater()

        self.schema = lib.gui_schema(
            self.schema_category, self.initial_schema_name
        )

        self.main_schema_key = self.schema["key"]

        self.add_children_gui(self.schema)
        self._update_values()

        self.hierarchical_style_update()

        self.set_state(CategoryState.Idle)

    def items_are_valid(self):
        has_invalid = False
        for item in self.input_fields:
            if item.child_invalid:
                has_invalid = True

        if not has_invalid:
            return True

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
        return False

    def on_saved(self, saved_tab_widget):
        """Callback on any tab widget save."""
        return

    def _save(self):
        self.set_state(CategoryState.Working)

        if self.items_are_valid():
            self.save()

            self._update_values()

        self.set_state(CategoryState.Idle)

        self.saved.emit(self)

    def _on_refresh(self):
        self.reset()

    def _on_hide_studio_overrides(self, state):
        self._hide_studio_overrides = (state == QtCore.Qt.Checked)
        self._update_values()

    def _save_as_defaults(self):
        if not self.items_are_valid():
            return

        all_values = {}
        for item in self.input_fields:
            all_values.update(item.config_value())

        for key in reversed(self.keys):
            all_values = {key: all_values}

        # Skip first key and convert data to store
        all_values = lib.convert_gui_data_with_metadata(
            all_values[self.main_schema_key]
        )

        if not self.validate_defaults_to_save(all_values):
            return

        defaults_dir = self.defaults_dir()
        keys_to_file = lib.file_keys_from_schema(self.schema)
        for key_sequence in keys_to_file:
            # Skip first key
            key_sequence = key_sequence[1:]
            subpath = "/".join(key_sequence) + ".json"

            new_values = all_values
            for key in key_sequence:
                new_values = new_values[key]

            output_path = os.path.join(defaults_dir, subpath)
            dirpath = os.path.dirname(output_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            print("Saving data to: ", subpath)
            with open(output_path, "w") as file_stream:
                json.dump(new_values, file_stream, indent=4)

        reset_default_settings()

        self._update_values()

    def _update_values(self):
        self.ignore_value_changes = True
        self.update_values()
        self.ignore_value_changes = False

    def add_children_gui(self, child_configuration):
        klass = lib.TypeToKlass.types.get(child_configuration["type"])
        item = klass(child_configuration, self)
        item.create_ui()
        self.input_fields.append(item)
        self.content_layout.addWidget(item, 0)

        # Add spacer to stretch children guis
        self.content_layout.addWidget(
            QtWidgets.QWidget(self.content_widget), 1
        )


class IgnoreInputChangesObj:
    def __init__(self, top_widget):
        self._ignore_changes = False
        self.top_widget = top_widget

    def __bool__(self):
        return self._ignore_changes

    def set_ignore(self, ignore_changes=True):
        if self._ignore_changes == ignore_changes:
            return
        self._ignore_changes = ignore_changes
        if not ignore_changes:
            self.top_widget.hierarchical_style_update()


class SystemWidget(SettingsCategoryWidget):
    schema_category = "system_schema"
    initial_schema_name = "schema_main"

    def initialize_attributes(self, *args, **kwargs):
        self._hide_studio_overrides = False
        self.ignore_input_changes = IgnoreInputChangesObj(self)

        self.keys = []
        self.input_fields = []

    def defaults_dir(self):
        print("*** defaults_dir")

    def validate_defaults_to_save(self, values):
        print("*** validate_defaults_to_save")

    def items_are_valid(self):
        invalid_items = self.get_invalid()
        if not invalid_items:
            return True

        msg_box = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Warning,
            "Invalid input",
            "There is invalid value in one of inputs."
            " Please lead red color and fix them.",
            parent=self
        )
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.exec_()

        first_invalid_item = invalid_items[0]
        self.scroll_widget.ensureWidgetVisible(first_invalid_item)
        if first_invalid_item.isVisible():
            first_invalid_item.setFocus(True)
        return False

    def save(self):
        if self.items_are_valid():
            self.entity.save()
            # NOTE There are relations to previous entities and C++ callbacks
            #   so it is easier to just use new entity and recreate UI but
            #   would be nice to change this and add cleanup part so this is
            #   not required.
            self.reset()

    def get_invalid(self):
        invalid = []
        for input_field in self.input_fields:
            invalid.extend(input_field.get_invalid())
        return invalid

    def update_values(self):
        # TODO remove as it breaks entities. Was used in previous
        #   implementation of category widget.
        pass

    def create_ui(self):
        self.modify_defaults_checkbox = None

        scroll_widget = QtWidgets.QScrollArea(self)
        scroll_widget.setObjectName("GroupWidget")
        content_widget = QtWidgets.QWidget(scroll_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)
        content_layout.setSpacing(5)
        content_layout.setAlignment(QtCore.Qt.AlignTop)

        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(content_widget)

        configurations_widget = QtWidgets.QWidget(self)

        footer_widget = QtWidgets.QWidget(configurations_widget)
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)

        if self.user_role == "developer":
            self._add_developer_ui(footer_layout)

        save_btn = QtWidgets.QPushButton("Save")
        spacer_widget = QtWidgets.QWidget()
        footer_layout.addWidget(spacer_widget, 1)
        footer_layout.addWidget(save_btn, 0)

        configurations_layout = QtWidgets.QVBoxLayout(configurations_widget)
        configurations_layout.setContentsMargins(0, 0, 0, 0)
        configurations_layout.setSpacing(0)

        configurations_layout.addWidget(scroll_widget, 1)
        configurations_layout.addWidget(footer_widget, 0)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(configurations_widget, 1)

        save_btn.clicked.connect(self._save)

        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget
        self.configurations_widget = configurations_widget
        self.main_layout = main_layout

        self.ui_tweaks()

    def _add_developer_ui(self, footer_layout):
        refresh_icon = qtawesome.icon("fa.refresh", color="white")
        refresh_button = QtWidgets.QPushButton()
        refresh_button.setIcon(refresh_icon)

        modify_defaults_widget = QtWidgets.QWidget()
        modify_defaults_checkbox = QtWidgets.QCheckBox(modify_defaults_widget)
        modify_defaults_checkbox.setChecked(self._hide_studio_overrides)
        label_widget = QtWidgets.QLabel(
            "Modify defaults", modify_defaults_widget
        )

        modify_defaults_layout = QtWidgets.QHBoxLayout(modify_defaults_widget)
        modify_defaults_layout.addWidget(label_widget)
        modify_defaults_layout.addWidget(modify_defaults_checkbox)

        footer_layout.addWidget(refresh_button, 0)
        footer_layout.addWidget(modify_defaults_widget, 0)

        refresh_button.clicked.connect(self._on_refresh)
        modify_defaults_checkbox.stateChanged.connect(
            self._on_modify_defaults
        )
        self.modify_defaults_checkbox = modify_defaults_checkbox

    def _on_modify_defaults(self):
        if self.modify_defaults_checkbox.isChecked():
            if not self.entity.is_in_defaults_state():
                self.reset()
        else:
            if not self.entity.is_in_studio_state():
                self.reset()

    def reset(self):
        self.set_state(CategoryState.Working)

        self.input_fields = []

        while self.content_layout.count() != 0:
            widget = self.content_layout.itemAt(0).widget()
            widget.hide()
            self.content_layout.removeWidget(widget)
            widget.deleteLater()

        self.entity = base_entity.SystemRootEntity()
        self.entity.on_change_callbacks.append(self._on_entity_change)
        try:
            if (
                self.modify_defaults_checkbox
                and self.modify_defaults_checkbox.isChecked()
            ):
                self.entity.set_defaults_state()
            else:
                self.entity.set_studio_state()

            if self.modify_defaults_checkbox:
                self.modify_defaults_checkbox.setEnabled(True)
        except DefaultsNotDefined:
            if not self.modify_defaults_checkbox:
                msg_box = QtWidgets.QMessageBox(
                    "BUG: Default values are not set and you"
                    " don't have permissions to modify them."
                )
                msg_box.exec_()
                return

            self.entity.set_defaults_state()
            self.modify_defaults_checkbox.setChecked(True)
            self.modify_defaults_checkbox.setEnabled(False)

        self.add_children_gui()

        self.ignore_input_changes.set_ignore(True)

        for input_field in self.input_fields:
            input_field.set_entity_value()

        self.ignore_input_changes.set_ignore(False)

        self.set_state(CategoryState.Idle)

    def _on_entity_change(self):
        self.hierarchical_style_update()

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def add_widget_to_layout(self, widget, label_widget=None):
        if label_widget:
            raise NotImplementedError(
                "`add_widget_to_layout` is not implemented on Category item"
            )
        self.content_layout.addWidget(widget, 0)

    def add_children_gui(self):
        for child_obj in self.entity.children:
            item = self.create_ui_for_entity(child_obj, self)
            self.input_fields.append(item)

        # Add spacer to stretch children guis
        self.content_layout.addWidget(
            QtWidgets.QWidget(self.content_widget), 1
        )


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

        self.dbcon = None

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

        system_settings = get_system_settings()
        mongo_url = system_settings["modules"]["avalon"]["AVALON_MONGO"]
        if not mongo_url:
            mongo_url = os.environ["PYPE_MONGO"]

        # Force uninstall of whole avalon connection if url does not match
        # to current environment and set it as environment
        if mongo_url != os.environ["AVALON_MONGO"]:
            AvalonMongoConnection.uninstall(self.dbcon, force=True)
            os.environ["AVALON_MONGO"] = mongo_url
            self.dbcon = None

        if not self.dbcon:
            try:
                self.dbcon = AvalonMongoDB()
                self.dbcon.install()
            except Exception:
                self.dbcon = None
                self.current_project = None

        if self.dbcon:
            for project_doc in tuple(self.dbcon.projects()):
                items.append(project_doc["name"])

        for item in items:
            model.appendRow(QtGui.QStandardItem(item))

        self.select_project(selected_project)

        self.current_project = self.project_list.currentIndex().data(
            QtCore.Qt.DisplayRole
        )


class ProjectWidget(SettingsCategoryWidget):
    schema_category = "projects_schema"
    initial_schema_name = "schema_main"

    def initialize_attributes(self):
        self.project_name = None

        super(ProjectWidget, self).initialize_attributes()

    def ui_tweaks(self):
        project_list_widget = ProjectListWidget(self)
        project_list_widget.refresh()

        self.main_layout.insertWidget(0, project_list_widget, 0)

        project_list_widget.project_changed.connect(self._on_project_change)

        self.project_list_widget = project_list_widget

    def defaults_dir(self):
        return DEFAULTS_DIR

    def validate_defaults_to_save(self, _):
        # Projects does not have any specific validations
        return True

    def on_saved(self, saved_tab_widget):
        """Callback on any tab widget save.

        Check if AVALON_MONGO is still same.
        """
        if self is saved_tab_widget:
            return

        system_settings = get_system_settings()
        mongo_url = system_settings["modules"]["avalon"]["AVALON_MONGO"]
        if not mongo_url:
            mongo_url = os.environ["PYPE_MONGO"]

        # If mongo url is not the same as was then refresh projects
        if mongo_url != os.environ["AVALON_MONGO"]:
            self.project_list_widget.refresh()

    def _on_project_change(self):
        self.set_state(CategoryState.Working)

        project_name = self.project_list_widget.project_name()
        if project_name is None:
            _project_overrides = lib.NOT_SET
            _project_anatomy = lib.NOT_SET
            self.is_overidable = False
        else:
            _project_overrides = get_project_settings_overrides(project_name)
            _project_anatomy = get_project_anatomy_overrides(project_name)
            self.is_overidable = True

        overrides = {self.main_schema_key: {
            PROJECT_SETTINGS_KEY: lib.convert_overrides_to_gui_data(
                _project_overrides
            ),
            PROJECT_ANATOMY_KEY: lib.convert_overrides_to_gui_data(
                _project_anatomy
            )
        }}
        self.project_name = project_name
        self.ignore_value_changes = True
        for item in self.input_fields:
            item.apply_overrides(overrides)
        self.ignore_value_changes = False

        self.set_state(CategoryState.Idle)

    def save(self):
        data = {}
        studio_overrides = bool(self.project_name is None)
        for item in self.input_fields:
            if studio_overrides:
                value, _is_group = item.studio_overrides()
            else:
                value, _is_group = item.overrides()
            if value is not lib.NOT_SET:
                data.update(value)

        output_data = lib.convert_gui_data_to_overrides(
            data.get(self.main_schema_key) or {}
        )

        # Saving overrides data
        project_overrides_data = output_data.get(PROJECT_SETTINGS_KEY, {})
        save_project_settings(self.project_name, project_overrides_data)

        # Saving anatomy data
        project_anatomy_data = output_data.get(PROJECT_ANATOMY_KEY, {})
        save_project_anatomy(self.project_name, project_anatomy_data)

    def update_values(self):
        if self.project_name is not None:
            self._on_project_change()
            return

        default_values = lib.convert_data_to_gui_data(
            {self.main_schema_key: get_default_settings()}
        )
        for input_field in self.input_fields:
            input_field.update_default_values(default_values)

        if self._hide_studio_overrides:
            studio_values = lib.NOT_SET
        else:
            studio_values = lib.convert_overrides_to_gui_data({
                self.main_schema_key: {
                    PROJECT_SETTINGS_KEY: (
                        get_studio_project_settings_overrides()
                    ),
                    PROJECT_ANATOMY_KEY: (
                        get_studio_project_anatomy_overrides()
                    )
                }
            })

        for input_field in self.input_fields:
            input_field.update_studio_values(studio_values)
