import sys
import traceback
import contextlib
from enum import Enum
from Qt import QtWidgets, QtCore
import qtawesome

from openpype.lib import get_openpype_version
from openpype.tools.utils import set_style_property
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
from .widgets import (
    ProjectListWidget,
    VersionAction
)
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
    reset_started = QtCore.Signal()
    reset_finished = QtCore.Signal()
    full_path_requested = QtCore.Signal(str, str)

    require_restart_label_text = (
        "Your changes require restart of"
        " all running OpenPype processes to take affect."
    )
    outdated_version_label_text = (
        "Your settings are loaded from an older version."
    )
    source_version_tooltip = "Using settings of current OpenPype version"
    source_version_tooltip_outdated = (
        "Please check that all settings are still correct (blue colour\n"
        "indicates potential changes in the new version) and save your\n"
        "settings to update them to you current running OpenPype version."
    )

    def __init__(self, user_role, parent=None):
        super(SettingsCategoryWidget, self).__init__(parent)

        self.user_role = user_role

        self.entity = None

        self._state = CategoryState.Idle

        self._hide_studio_overrides = False
        self._updating_root = False
        self._use_version = None
        self._current_version = get_openpype_version()

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

    @property
    def is_modifying_defaults(self):
        if self.modify_defaults_checkbox is None:
            return False
        return self.modify_defaults_checkbox.isChecked()

    def create_ui(self):
        self.modify_defaults_checkbox = None

        conf_wrapper_widget = QtWidgets.QWidget(self)
        configurations_widget = QtWidgets.QWidget(conf_wrapper_widget)

        # Breadcrumbs/Path widget
        breadcrumbs_widget = QtWidgets.QWidget(self)
        breadcrumbs_label = QtWidgets.QLabel("Path:", breadcrumbs_widget)
        breadcrumbs_bar = BreadcrumbsAddressBar(breadcrumbs_widget)

        refresh_icon = qtawesome.icon("fa.refresh", color="white")
        refresh_btn = QtWidgets.QPushButton(breadcrumbs_widget)
        refresh_btn.setIcon(refresh_icon)

        breadcrumbs_layout = QtWidgets.QHBoxLayout(breadcrumbs_widget)
        breadcrumbs_layout.setContentsMargins(5, 5, 5, 5)
        breadcrumbs_layout.setSpacing(5)
        breadcrumbs_layout.addWidget(breadcrumbs_label, 0)
        breadcrumbs_layout.addWidget(breadcrumbs_bar, 1)
        breadcrumbs_layout.addWidget(refresh_btn, 0)

        # Widgets representing settings entities
        scroll_widget = QtWidgets.QScrollArea(configurations_widget)
        content_widget = QtWidgets.QWidget(scroll_widget)
        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(content_widget)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)
        content_layout.setSpacing(5)
        content_layout.setAlignment(QtCore.Qt.AlignTop)

        # Footer widget
        footer_widget = QtWidgets.QWidget(self)
        footer_widget.setObjectName("SettingsFooter")

        # Info labels
        # TODO dynamic labels
        labels_alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        empty_label = QtWidgets.QLabel(footer_widget)

        outdated_version_label = QtWidgets.QLabel(
            self.outdated_version_label_text, footer_widget
        )
        outdated_version_label.setToolTip(self.source_version_tooltip_outdated)
        outdated_version_label.setAlignment(labels_alignment)
        outdated_version_label.setVisible(False)
        outdated_version_label.setObjectName("SettingsOutdatedSourceVersion")

        require_restart_label = QtWidgets.QLabel(
            self.require_restart_label_text, footer_widget
        )
        require_restart_label.setAlignment(labels_alignment)
        require_restart_label.setVisible(False)

        # Label showing source version of loaded settings
        source_version_label = QtWidgets.QLabel("", footer_widget)
        source_version_label.setObjectName("SourceVersionLabel")
        set_style_property(source_version_label, "state", "")
        source_version_label.setToolTip(self.source_version_tooltip)

        save_btn = QtWidgets.QPushButton("Save", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(5, 5, 5, 5)
        if self.user_role == "developer":
            self._add_developer_ui(footer_layout, footer_widget)

        footer_layout.addWidget(empty_label, 1)
        footer_layout.addWidget(outdated_version_label, 1)
        footer_layout.addWidget(require_restart_label, 1)
        footer_layout.addWidget(source_version_label, 0)
        footer_layout.addWidget(save_btn, 0)

        configurations_layout = QtWidgets.QVBoxLayout(configurations_widget)
        configurations_layout.setContentsMargins(0, 0, 0, 0)
        configurations_layout.setSpacing(0)

        configurations_layout.addWidget(scroll_widget, 1)

        conf_wrapper_layout = QtWidgets.QHBoxLayout(conf_wrapper_widget)
        conf_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        conf_wrapper_layout.setSpacing(0)
        conf_wrapper_layout.addWidget(configurations_widget, 1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(breadcrumbs_widget, 0)
        main_layout.addWidget(conf_wrapper_widget, 1)
        main_layout.addWidget(footer_widget, 0)

        save_btn.clicked.connect(self._save)
        refresh_btn.clicked.connect(self._on_refresh)
        breadcrumbs_bar.path_edited.connect(self._on_path_edit)

        self._require_restart_label = require_restart_label
        self._outdated_version_label = outdated_version_label
        self._empty_label = empty_label

        self._is_loaded_version_outdated = False

        self.save_btn = save_btn
        self._source_version_label = source_version_label

        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget
        self.breadcrumbs_bar = breadcrumbs_bar

        self.breadcrumbs_model = None
        self.refresh_btn = refresh_btn

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

    def change_path(self, path):
        """Change path and go to widget."""
        self.breadcrumbs_bar.change_path(path)

    def set_path(self, path):
        """Called from clicked widget."""
        self.breadcrumbs_bar.set_path(path)

    def _add_developer_ui(self, footer_layout, footer_widget):
        modify_defaults_checkbox = QtWidgets.QCheckBox(footer_widget)
        modify_defaults_checkbox.setChecked(self._hide_studio_overrides)
        label_widget = QtWidgets.QLabel(
            "Modify defaults", footer_widget
        )

        footer_layout.addWidget(label_widget, 0)
        footer_layout.addWidget(modify_defaults_checkbox, 0)

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
            self._use_version = None

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
        self._update_labels_visibility()

    def reset(self):
        self.reset_started.emit()
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
        self._updating_root = True
        source_version = ""
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
            source_version = self.entity.source_version

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

        self._updating_root = False

        # Update source version label
        state_value = ""
        tooltip = ""
        outdated = False
        if source_version:
            if source_version != self._current_version:
                state_value = "different"
                tooltip = self.source_version_tooltip_outdated
                outdated = True
            else:
                state_value = "same"
                tooltip = self.source_version_tooltip

        self._is_loaded_version_outdated = outdated
        self._source_version_label.setText(source_version)
        self._source_version_label.setToolTip(tooltip)
        set_style_property(self._source_version_label, "state", state_value)
        self._update_labels_visibility()

        self.set_state(CategoryState.Idle)

        if dialog:
            dialog.exec_()
            self._on_reset_crash()
        else:
            self._on_reset_success()
        self.reset_finished.emit()

    def _on_source_version_change(self, version):
        if self._updating_root:
            return

        if version == self._current_version:
            version = None

        self._use_version = version
        QtCore.QTimer.singleShot(20, self.reset)

    def add_context_actions(self, menu):
        if not self.entity or self.is_modifying_defaults:
            return

        versions = self.entity.get_available_studio_versions(sorted=True)
        if not versions:
            return

        submenu = QtWidgets.QMenu("Use settings from version", menu)
        for version in reversed(versions):
            action = VersionAction(version, submenu)
            action.version_triggered.connect(
                self._on_context_version_trigger
            )
            submenu.addAction(action)
        menu.addMenu(submenu)

    def _on_context_version_trigger(self, version):
        self._on_source_version_change(version)

    def _on_reset_crash(self):
        self.save_btn.setEnabled(False)

        if self.breadcrumbs_model is not None:
            self.breadcrumbs_model.set_entity(None)

    def _on_reset_success(self):
        if not self.save_btn.isEnabled():
            self.save_btn.setEnabled(True)

        if self.breadcrumbs_model is not None:
            path = self.breadcrumbs_bar.path()
            self.breadcrumbs_bar.set_path("")
            self.breadcrumbs_model.set_entity(self.entity)
            self.breadcrumbs_bar.change_path(path)

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
        if self.is_modifying_defaults:
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

    def _update_labels_visibility(self):
        visible_label = None
        labels = {
            self._empty_label,
            self._outdated_version_label,
            self._require_restart_label,
        }
        if self.is_modifying_defaults or self.entity is None:
            require_restart = False
        else:
            require_restart = self.entity.require_restart

        if require_restart:
            visible_label = self._require_restart_label
        elif self._is_loaded_version_outdated:
            visible_label = self._outdated_version_label
        else:
            visible_label = self._empty_label

        if visible_label.isVisible():
            return

        for label in labels:
            if label is visible_label:
                visible_label.setVisible(True)
            else:
                label.setVisible(False)

    def _on_refresh(self):
        self.reset()

    def _on_hide_studio_overrides(self, state):
        self._hide_studio_overrides = (state == QtCore.Qt.Checked)


class SystemWidget(SettingsCategoryWidget):
    def __init__(self, *args, **kwargs):
        self._actions = []
        super(SystemWidget, self).__init__(*args, **kwargs)

    def contain_category_key(self, category):
        if category == "system_settings":
            return True
        return False

    def set_category_path(self, category, path):
        self.breadcrumbs_bar.change_path(path)

    def _create_root_entity(self):
        entity = SystemSettings(
            set_studio_state=False, source_version=self._use_version
        )
        entity.on_change_callbacks.append(self._on_entity_change)
        self.entity = entity
        try:
            if self.is_modifying_defaults:
                entity.set_defaults_state()
            else:
                entity.set_studio_state()

            if self.modify_defaults_checkbox:
                self.modify_defaults_checkbox.setEnabled(True)
        except DefaultsNotDefined:
            if not self.modify_defaults_checkbox:
                raise

            entity.set_defaults_state()
            self.modify_defaults_checkbox.setChecked(True)
            self.modify_defaults_checkbox.setEnabled(False)

    def ui_tweaks(self):
        self.breadcrumbs_model = SystemSettingsBreadcrumbs()
        self.breadcrumbs_bar.set_model(self.breadcrumbs_model)

    def _on_modify_defaults(self):
        if self.is_modifying_defaults:
            if not self.entity.is_in_defaults_state():
                self.reset()
        else:
            if not self.entity.is_in_studio_state():
                self.reset()


class ProjectWidget(SettingsCategoryWidget):
    def __init__(self, *args, **kwargs):
        super(ProjectWidget, self).__init__(*args, **kwargs)

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

        self.breadcrumbs_bar.change_path(path)

    def initialize_attributes(self):
        self.project_name = None

    def ui_tweaks(self):
        self.breadcrumbs_model = ProjectSettingsBreadcrumbs()
        self.breadcrumbs_bar.set_model(self.breadcrumbs_model)

        project_list_widget = ProjectListWidget(self)

        self.conf_wrapper_layout.insertWidget(0, project_list_widget, 0)

        project_list_widget.project_changed.connect(self._on_project_change)
        project_list_widget.version_change_requested.connect(
            self._on_source_version_change
        )

        self.project_list_widget = project_list_widget

    def get_project_names(self):
        if self.is_modifying_defaults:
            return []
        return self.project_list_widget.get_project_names()

    def on_saved(self, saved_tab_widget):
        """Callback on any tab widget save.

        Check if AVALON_MONGO is still same.
        """
        if self is saved_tab_widget:
            return

    def _on_context_version_trigger(self, version):
        self.project_list_widget.select_project(None)
        super(ProjectWidget, self)._on_context_version_trigger(version)

    def _on_reset_start(self):
        self.project_list_widget.refresh()

    def _on_reset_crash(self):
        self._set_enabled_project_list(False)
        super(ProjectWidget, self)._on_reset_crash()

    def _on_reset_success(self):
        self._set_enabled_project_list(True)
        super(ProjectWidget, self)._on_reset_success()

    def _set_enabled_project_list(self, enabled):
        if enabled and self.is_modifying_defaults:
            enabled = False
        if self.project_list_widget.isEnabled() != enabled:
            self.project_list_widget.setEnabled(enabled)

    def _create_root_entity(self):
        entity = ProjectSettings(
            change_state=False, source_version=self._use_version
        )
        entity.on_change_callbacks.append(self._on_entity_change)
        self.project_list_widget.set_entity(entity)
        self.entity = entity
        try:
            if self.is_modifying_defaults:
                self.entity.set_defaults_state()

            elif self.project_name is None:
                self.entity.set_studio_state()

            else:
                self.entity.change_project(
                    self.project_name, self._use_version
                )

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
        if self.is_modifying_defaults:
            self._set_enabled_project_list(False)
            if not self.entity.is_in_defaults_state():
                self.reset()
        else:
            self._set_enabled_project_list(True)
            if not self.entity.is_in_studio_state():
                self.reset()
