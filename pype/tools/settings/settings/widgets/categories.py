import os
from enum import Enum
from Qt import QtWidgets, QtCore, QtGui

from pype.settings.entities import (
    SystemSettings,
    ProjectSettings,

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

    DefaultsNotDefined,
    StudioDefaultsNotDefined
)

from pype.settings.lib import get_system_settings
from .widgets import ProjectListWidget

from . import lib

from .base import GUIWidget
from .list_item_widget import ListWidget
from .list_strict_widget import ListStrictWidget
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

from avalon.vendor import qtawesome


class CategoryState(Enum):
    Idle = object()
    Working = object()


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


class SettingsCategoryWidget(QtWidgets.QWidget):
    state_changed = QtCore.Signal()
    saved = QtCore.Signal(QtWidgets.QWidget)

    def __init__(self, user_role, parent=None):
        super(SettingsCategoryWidget, self).__init__(parent)

        self.user_role = user_role

        self.entity = None

        self._state = CategoryState.Idle

        self._hide_studio_overrides = False
        self.ignore_input_changes = IgnoreInputChangesObj(self)

        self.keys = []
        self.input_fields = []

        self.initialize_attributes()

        self.create_ui()

    @staticmethod
    def create_ui_for_entity(category_widget, entity, entity_widget):
        args = (category_widget, entity, entity_widget)
        if isinstance(entity, GUIEntity):
            return GUIWidget(*args)

        elif isinstance(entity, DictImmutableKeysEntity):
            return DictImmutableKeysWidget(*args)

        elif isinstance(entity, BoolEntity):
            return BoolWidget(*args)

        elif isinstance(entity, TextEntity):
            return TextWidget(*args)

        elif isinstance(entity, NumberEntity):
            return NumberWidget(*args)

        elif isinstance(entity, RawJsonEntity):
            return RawJsonWidget(*args)

        elif isinstance(entity, EnumEntity):
            return EnumeratorWidget(*args)

        elif isinstance(entity, PathEntity):
            return PathWidget(*args)

        elif isinstance(entity, PathInput):
            return PathInputWidget(*args)

        elif isinstance(entity, ListEntity):
            return ListWidget(*args)

        elif isinstance(entity, DictMutableKeysEntity):
            return DictMutableKeysWidget(*args)

        elif isinstance(entity, ListStrictEntity):
            return ListStrictWidget(*args)

        label = "<{}>: {} ({})".format(
            entity.__class__.__name__, entity.path, entity.value
        )
        raise TypeError("Unknown type: {}".format(label))

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
        return

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

    def ui_tweaks(self):
        return

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

    def get_invalid(self):
        invalid = []
        for input_field in self.input_fields:
            invalid.extend(input_field.get_invalid())
        return invalid

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def _on_entity_change(self):
        self.hierarchical_style_update()

    def add_widget_to_layout(self, widget, label_widget=None):
        if label_widget:
            raise NotImplementedError(
                "`add_widget_to_layout` on Category item can't accept labels"
            )
        self.content_layout.addWidget(widget, 0)

    def save(self):
        if self.items_are_valid():
            self.entity.save()
            # NOTE There are relations to previous entities and C++ callbacks
            #   so it is easier to just use new entity and recreate UI but
            #   would be nice to change this and add cleanup part so this is
            #   not required.
            self.reset()

    def _create_root_entity(self):
        raise NotImplementedError(
            "`create_root_entity` method not implemented"
        )

    def reset(self):
        self.set_state(CategoryState.Working)

        self.input_fields = []

        while self.content_layout.count() != 0:
            widget = self.content_layout.itemAt(0).widget()
            widget.hide()
            self.content_layout.removeWidget(widget)
            widget.deleteLater()

        self._create_root_entity()

        self.add_children_gui()

        self.ignore_input_changes.set_ignore(True)

        for input_field in self.input_fields:
            input_field.set_entity_value()

        self.ignore_input_changes.set_ignore(False)

        self.set_state(CategoryState.Idle)

    def add_children_gui(self):
        for child_obj in self.entity.children:
            item = self.create_ui_for_entity(self, child_obj, self)
            self.input_fields.append(item)

        # Add spacer to stretch children guis
        self.content_layout.addWidget(
            QtWidgets.QWidget(self.content_widget), 1
        )

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

    def on_saved(self, saved_tab_widget):
        """Callback on any tab widget save."""
        return

    def _save(self):
        self.set_state(CategoryState.Working)

        if self.items_are_valid():
            self.save()

        self.set_state(CategoryState.Idle)

        self.saved.emit(self)

    def _on_refresh(self):
        self.reset()

    def _on_hide_studio_overrides(self, state):
        self._hide_studio_overrides = (state == QtCore.Qt.Checked)


class SystemWidget(SettingsCategoryWidget):
    def _create_root_entity(self):
        self.entity = SystemSettings(set_studio_state=False)
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

    def _on_modify_defaults(self):
        if self.modify_defaults_checkbox.isChecked():
            if not self.entity.is_in_defaults_state():
                self.reset()
        else:
            if not self.entity.is_in_studio_state():
                self.reset()


class ProjectWidget(SettingsCategoryWidget):
    def initialize_attributes(self):
        self.project_name = None

    def ui_tweaks(self):
        project_list_widget = ProjectListWidget(self)
        project_list_widget.refresh()

        self.main_layout.insertWidget(0, project_list_widget, 0)

        project_list_widget.project_changed.connect(self._on_project_change)

        self.project_list_widget = project_list_widget

    def on_saved(self, saved_tab_widget):
        """Callback on any tab widget save.

        Check if AVALON_MONGO is still same.
        """
        if self is saved_tab_widget:
            return

    def _create_root_entity(self):
        self.entity = ProjectSettings(change_state=False)
        self.entity.on_change_callbacks.append(self._on_entity_change)
        try:
            if (
                self.modify_defaults_checkbox
                and self.modify_defaults_checkbox.isChecked()
            ):
                self.entity.set_defaults_state()

            elif self.project_name is None:
                self.entity.set_studio_state()

            elif self.project_name == self.entity.project_name:
                self.entity.set_project_state()
            else:
                self.entity.change_project(self.project_name)

            if self.modify_defaults_checkbox:
                self.modify_defaults_checkbox.setEnabled(True)
            self.project_list_widget.setEnabled(True)

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
            self.project_list_widget.setEnabled(False)

        except StudioDefaultsNotDefined:
            self.select_default_project()

    def _on_project_change(self):
        project_name = self.project_list_widget.project_name()
        if project_name == self.project_name:
            return

        self.project_name = project_name

        self.set_state(CategoryState.Working)

        self.reset()

        self.set_state(CategoryState.Idle)

    def _on_modify_defaults(self):
        if self.modify_defaults_checkbox.isChecked():
            if not self.entity.is_in_defaults_state():
                self.reset()
        else:
            if not self.entity.is_in_studio_state():
                self.reset()
