import os
import sys
import traceback
import contextlib
from enum import Enum
from Qt import QtWidgets, QtCore, QtGui

from openpype.settings.entities import (
    SystemSettings,
    ProjectSettings,

    GUIEntity,
    DictImmutableKeysEntity,
    DictMutableKeysEntity,
    DictConditionalEntity,
    ListEntity,
    PathEntity,
    ListStrictEntity,

    NumberEntity,
    BoolEntity,
    BaseEnumEntity,
    TextEntity,
    PathInput,
    RawJsonEntity,
    ColorEntity,

    DefaultsNotDefined,
    StudioDefaultsNotDefined,
    SchemaError
)
from openpype.settings.entities.op_version_entity import (
    OpenPypeVersionInput
)

from openpype.settings import SaveWarningExc
from .widgets import ProjectListWidget
from .breadcrumbs_widget import (
    BreadcrumbsAddressBar,
    SystemSettingsBreadcrumbs,
    ProjectSettingsBreadcrumbs
)

from .base import GUIWidget
from .list_item_widget import ListWidget
from .list_strict_widget import ListStrictWidget
from .dict_mutable_widget import DictMutableKeysWidget
from .dict_conditional import DictConditionalWidget
from .item_widgets import (
    BoolWidget,
    DictImmutableKeysWidget,
    TextWidget,
    OpenPypeVersionText,
    NumberWidget,
    RawJsonWidget,
    EnumeratorWidget,
    PathWidget,
    PathInputWidget
)
from .color_widget import ColorWidget
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
    restart_required_trigger = QtCore.Signal()
    full_path_requested = QtCore.Signal(str, str)

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

        elif isinstance(entity, DictConditionalEntity):
            return DictConditionalWidget(*args)

        elif isinstance(entity, DictImmutableKeysEntity):
            return DictImmutableKeysWidget(*args)

        elif isinstance(entity, BoolEntity):
            return BoolWidget(*args)

        elif isinstance(entity, OpenPypeVersionInput):
            return OpenPypeVersionText(*args)

        elif isinstance(entity, TextEntity):
            return TextWidget(*args)

        elif isinstance(entity, NumberEntity):
            return NumberWidget(*args)

        elif isinstance(entity, RawJsonEntity):
            return RawJsonWidget(*args)

        elif isinstance(entity, ColorEntity):
            return ColorWidget(*args)

        elif isinstance(entity, BaseEnumEntity):
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

        breadcrumbs_label = QtWidgets.QLabel("Path:", content_widget)
        breadcrumbs_widget = BreadcrumbsAddressBar(content_widget)

        breadcrumbs_layout = QtWidgets.QHBoxLayout()
        breadcrumbs_layout.setContentsMargins(5, 5, 5, 5)
        breadcrumbs_layout.setSpacing(5)
        breadcrumbs_layout.addWidget(breadcrumbs_label)
        breadcrumbs_layout.addWidget(breadcrumbs_widget)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)
        content_layout.setSpacing(5)
        content_layout.setAlignment(QtCore.Qt.AlignTop)

        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(content_widget)

        refresh_icon = qtawesome.icon("fa.refresh", color="white")
        refresh_btn = QtWidgets.QPushButton(self)
        refresh_btn.setIcon(refresh_icon)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.setContentsMargins(5, 5, 5, 5)
        if self.user_role == "developer":
            self._add_developer_ui(footer_layout)

        save_btn = QtWidgets.QPushButton("Save", self)
        require_restart_label = QtWidgets.QLabel(self)
        require_restart_label.setAlignment(QtCore.Qt.AlignCenter)

        footer_layout.addWidget(refresh_btn, 0)
        footer_layout.addWidget(require_restart_label, 1)
        footer_layout.addWidget(save_btn, 0)

        configurations_layout = QtWidgets.QVBoxLayout()
        configurations_layout.setContentsMargins(0, 0, 0, 0)
        configurations_layout.setSpacing(0)

        configurations_layout.addWidget(scroll_widget, 1)
        configurations_layout.addLayout(footer_layout, 0)

        conf_wrapper_layout = QtWidgets.QHBoxLayout()
        conf_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        conf_wrapper_layout.setSpacing(0)
        conf_wrapper_layout.addLayout(configurations_layout, 1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addLayout(breadcrumbs_layout, 0)
        main_layout.addLayout(conf_wrapper_layout, 1)

        save_btn.clicked.connect(self._save)
        refresh_btn.clicked.connect(self._on_refresh)
        breadcrumbs_widget.path_edited.connect(self._on_path_edit)

        self.save_btn = save_btn
        self.refresh_btn = refresh_btn
        self.require_restart_label = require_restart_label
        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget
        self.breadcrumbs_widget = breadcrumbs_widget
        self.breadcrumbs_model = None
        self.conf_wrapper_layout = conf_wrapper_layout
        self.main_layout = main_layout

        self.ui_tweaks()

    def ui_tweaks(self):
        return

    def _on_path_edit(self, path):
        for input_field in self.input_fields:
            if input_field.make_sure_is_visible(path, True):
                break

    def scroll_to(self, widget):
        if widget:
            # Process events which happened before ensurence
            # - that is because some widgets could be not visible before
            #   this method was called and have incorrect size
            QtWidgets.QApplication.processEvents()
            # Scroll to widget
            self.scroll_widget.ensureWidgetVisible(widget)

    def go_to_fullpath(self, full_path):
        """Full path of settings entity which can lead to different category.

        Args:
            full_path (str): Full path to settings entity. It is expected that
                path starts with category name ("system_setting" etc.).
        """
        if not full_path:
            return
        items = full_path.split("/")
        category = items[0]
        path = ""
        if len(items) > 1:
            path = "/".join(items[1:])
        self.full_path_requested.emit(category, path)

    def contain_category_key(self, category):
        """Parent widget ask if category of full path lead to this widget.

        Args:
            category (str): The category name.

        Returns:
            bool: Passed category lead to this widget.
        """
        return False

    def set_category_path(self, category, path):
        """Change path of widget based on category full path."""
        pass

    def set_path(self, path):
        self.breadcrumbs_widget.set_path(path)

    def _add_developer_ui(self, footer_layout):
        modify_defaults_widget = QtWidgets.QWidget()
        modify_defaults_checkbox = QtWidgets.QCheckBox(modify_defaults_widget)
        modify_defaults_checkbox.setChecked(self._hide_studio_overrides)
        label_widget = QtWidgets.QLabel(
            "Modify defaults", modify_defaults_widget
        )

        modify_defaults_layout = QtWidgets.QHBoxLayout(modify_defaults_widget)
        modify_defaults_layout.addWidget(label_widget)
        modify_defaults_layout.addWidget(modify_defaults_checkbox)

        footer_layout.addWidget(modify_defaults_widget, 0)

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

    @contextlib.contextmanager
    def working_state_context(self):
        self.set_state(CategoryState.Working)
        yield
        self.set_state(CategoryState.Idle)

    def save(self):
        if not self.items_are_valid():
            return

        try:
            self.entity.save()

            # NOTE There are relations to previous entities and C++ callbacks
            #   so it is easier to just use new entity and recreate UI but
            #   would be nice to change this and add cleanup part so this is
            #   not required.
            self.reset()

        except SaveWarningExc as exc:
            warnings = [
                "<b>Settings were saved but few issues happened.</b>"
            ]
            for item in exc.warnings:
                warnings.append(item.replace("\n", "<br>"))

            msg = "<br><br>".join(warnings)

            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Save warnings")
            dialog.setText(msg)
            dialog.setIcon(QtWidgets.QMessageBox.Warning)
            dialog.exec_()

            self.reset()

        except Exception as exc:
            formatted_traceback = traceback.format_exception(*sys.exc_info())
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Unexpected error")
            msg = "Unexpected error happened!\n\nError: {}".format(str(exc))
            dialog.setText(msg)
            dialog.setDetailedText("\n".join(formatted_traceback))
            dialog.setIcon(QtWidgets.QMessageBox.Critical)

            line_widths = set()
            metricts = dialog.fontMetrics()
            for line in formatted_traceback:
                line_widths.add(metricts.width(line))
            max_width = max(line_widths)

            spacer = QtWidgets.QSpacerItem(
                max_width, 0,
                QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Expanding
            )
            layout = dialog.layout()
            layout.addItem(
                spacer, layout.rowCount(), 0, 1, layout.columnCount()
            )
            dialog.exec_()

    def _create_root_entity(self):
        raise NotImplementedError(
            "`create_root_entity` method not implemented"
        )

    def _on_reset_start(self):
        return

    def _on_require_restart_change(self):
        value = ""
        if self.entity.require_restart:
            value = (
                "Your changes require restart of"
                " all running OpenPype processes to take affect."
            )
        self.require_restart_label.setText(value)

    def reset(self):
        self.set_state(CategoryState.Working)

        self._on_reset_start()

        self.input_fields = []

        while self.content_layout.count() != 0:
            widget = self.content_layout.itemAt(0).widget()
            if widget is not None:
                widget.setVisible(False)

            self.content_layout.removeWidget(widget)
            widget.deleteLater()

        dialog = None
        try:
            self._create_root_entity()

            self.entity.add_require_restart_change_callback(
                self._on_require_restart_change
            )

            self.add_children_gui()

            self.ignore_input_changes.set_ignore(True)

            for input_field in self.input_fields:
                input_field.set_entity_value()

            self.ignore_input_changes.set_ignore(False)

        except DefaultsNotDefined:
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Missing default values")
            dialog.setText((
                "Default values are not set and you"
                " don't have permissions to modify them."
                " Please contact OpenPype team."
            ))
            dialog.setIcon(QtWidgets.QMessageBox.Critical)

        except SchemaError as exc:
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Schema error")
            msg = "Implementation bug!\n\nError: {}".format(str(exc))
            dialog.setText(msg)
            dialog.setIcon(QtWidgets.QMessageBox.Warning)

        except Exception as exc:
            formatted_traceback = traceback.format_exception(*sys.exc_info())
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Unexpected error")
            msg = "Unexpected error happened!\n\nError: {}".format(str(exc))
            dialog.setText(msg)
            dialog.setDetailedText("\n".join(formatted_traceback))
            dialog.setIcon(QtWidgets.QMessageBox.Critical)

            line_widths = set()
            metricts = dialog.fontMetrics()
            for line in formatted_traceback:
                line_widths.add(metricts.width(line))
            max_width = max(line_widths)

            spacer = QtWidgets.QSpacerItem(
                max_width, 0,
                QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Expanding
            )
            layout = dialog.layout()
            layout.addItem(
                spacer, layout.rowCount(), 0, 1, layout.columnCount()
            )

        self.set_state(CategoryState.Idle)

        if dialog:
            dialog.exec_()
            self._on_reset_crash()
        else:
            self._on_reset_success()

    def _on_reset_crash(self):
        self.save_btn.setEnabled(False)

        if self.breadcrumbs_model is not None:
            self.breadcrumbs_model.set_entity(None)

    def _on_reset_success(self):
        if not self.save_btn.isEnabled():
            self.save_btn.setEnabled(True)

        if self.breadcrumbs_model is not None:
            path = self.breadcrumbs_widget.path()
            self.breadcrumbs_widget.set_path("")
            self.breadcrumbs_model.set_entity(self.entity)
            self.breadcrumbs_widget.change_path(path)

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
            (
                "There is invalid value in one of inputs."
                " Please lead red color and fix them."
            ),
            parent=self
        )
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.exec_()

        first_invalid_item = invalid_items[0]
        self.scroll_widget.ensureWidgetVisible(first_invalid_item)
        if first_invalid_item.isVisible():
            first_invalid_item.setFocus()
        return False

    def on_saved(self, saved_tab_widget):
        """Callback on any tab widget save."""
        return

    def _save(self):
        # Don't trigger restart if defaults are modified
        if (
            self.modify_defaults_checkbox
            and self.modify_defaults_checkbox.isChecked()
        ):
            require_restart = False
        else:
            require_restart = self.entity.require_restart

        self.set_state(CategoryState.Working)

        if self.items_are_valid():
            self.save()

        self.set_state(CategoryState.Idle)

        self.saved.emit(self)

        if require_restart:
            self.restart_required_trigger.emit()
        self.require_restart_label.setText("")

    def _on_refresh(self):
        self.reset()

    def _on_hide_studio_overrides(self, state):
        self._hide_studio_overrides = (state == QtCore.Qt.Checked)


class SystemWidget(SettingsCategoryWidget):
    def contain_category_key(self, category):
        if category == "system_settings":
            return True
        return False

    def set_category_path(self, category, path):
        self.breadcrumbs_widget.change_path(path)

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
                raise

            self.entity.set_defaults_state()
            self.modify_defaults_checkbox.setChecked(True)
            self.modify_defaults_checkbox.setEnabled(False)

    def ui_tweaks(self):
        self.breadcrumbs_model = SystemSettingsBreadcrumbs()
        self.breadcrumbs_widget.set_model(self.breadcrumbs_model)

    def _on_modify_defaults(self):
        if self.modify_defaults_checkbox.isChecked():
            if not self.entity.is_in_defaults_state():
                self.reset()
        else:
            if not self.entity.is_in_studio_state():
                self.reset()


class ProjectWidget(SettingsCategoryWidget):
    def contain_category_key(self, category):
        if category in ("project_settings", "project_anatomy"):
            return True
        return False

    def set_category_path(self, category, path):
        if path:
            path_items = path.split("/")
            if path_items[0] not in ("project_settings", "project_anatomy"):
                path = "/".join([category, path])
        else:
            path = category

        self.breadcrumbs_widget.change_path(path)

    def initialize_attributes(self):
        self.project_name = None

    def ui_tweaks(self):
        self.breadcrumbs_model = ProjectSettingsBreadcrumbs()
        self.breadcrumbs_widget.set_model(self.breadcrumbs_model)

        project_list_widget = ProjectListWidget(self)

        self.conf_wrapper_layout.insertWidget(0, project_list_widget, 0)

        project_list_widget.project_changed.connect(self._on_project_change)

        self.project_list_widget = project_list_widget

    def get_project_names(self):
        if (
            self.modify_defaults_checkbox
            and self.modify_defaults_checkbox.isChecked()
        ):
            return []
        return self.project_list_widget.get_project_names()

    def on_saved(self, saved_tab_widget):
        """Callback on any tab widget save.

        Check if AVALON_MONGO is still same.
        """
        if self is saved_tab_widget:
            return

    def _on_reset_start(self):
        self.project_list_widget.refresh()

    def _on_reset_crash(self):
        self._set_enabled_project_list(False)
        super(ProjectWidget, self)._on_reset_crash()

    def _on_reset_success(self):
        self._set_enabled_project_list(True)
        super(ProjectWidget, self)._on_reset_success()

    def _set_enabled_project_list(self, enabled):
        if (
            enabled
            and self.modify_defaults_checkbox
            and self.modify_defaults_checkbox.isChecked()
        ):
            enabled = False
        if self.project_list_widget.isEnabled() != enabled:
            self.project_list_widget.setEnabled(enabled)

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

            self._set_enabled_project_list(True)

        except DefaultsNotDefined:
            if not self.modify_defaults_checkbox:
                raise

            self.entity.set_defaults_state()
            self.modify_defaults_checkbox.setChecked(True)
            self.modify_defaults_checkbox.setEnabled(False)
            self._set_enabled_project_list(False)

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
            self._set_enabled_project_list(False)
            if not self.entity.is_in_defaults_state():
                self.reset()
        else:
            self._set_enabled_project_list(True)
            if not self.entity.is_in_studio_state():
                self.reset()
