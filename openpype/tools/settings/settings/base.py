import sys
import json
import traceback
import functools

from Qt import QtWidgets, QtGui, QtCore

from openpype.settings.entities import ProjectSettings
from openpype.tools.settings import CHILD_OFFSET

from .widgets import ExpandingWidget
from .lib import create_deffered_value_change_timer
from .constants import DEFAULT_PROJECT_LABEL


class BaseWidget(QtWidgets.QWidget):
    allow_actions = True

    def __init__(self, category_widget, entity, entity_widget):
        self.category_widget = category_widget
        self.entity = entity
        self.entity_widget = entity_widget

        self.ignore_input_changes = entity_widget.ignore_input_changes

        self._is_invalid = False
        self._style_state = None

        super(BaseWidget, self).__init__(entity_widget.content_widget)
        if not self.entity.gui_type:
            self.entity.on_change_callbacks.append(self._on_entity_change)

        self.label_widget = None
        self.create_ui()

    @staticmethod
    def set_style_property(obj, property_name, property_value):
        """Change QWidget property and polish it's style."""
        if obj.property(property_name) == property_value:
            return

        obj.setProperty(property_name, property_value)
        obj.style().polish(obj)

    def scroll_to(self, widget):
        self.category_widget.scroll_to(widget)

    def set_path(self, path):
        self.category_widget.set_path(path)

    def set_focus(self, scroll_to=False):
        """Set focus of a widget.

        Args:
            scroll_to(bool): Also scroll to widget in category widget.
        """
        if scroll_to:
            self.scroll_to(self)
        self.setFocus()

    def make_sure_is_visible(self, path, scroll_to):
        """Make a widget of entity visible by it's path.

        Args:
            path(str): Path to entity.
            scroll_to(bool): Should be scrolled to entity.

        Returns:
            bool: Entity with path was found.
        """
        raise NotImplementedError(
            "{} not implemented `make_sure_is_visible`".format(
                self.__class__.__name__
            )
        )

    def trigger_hierarchical_style_update(self):
        self.category_widget.hierarchical_style_update()

    def create_ui_for_entity(self, *args, **kwargs):
        return self.category_widget.create_ui_for_entity(*args, **kwargs)

    @property
    def is_invalid(self):
        return self._is_invalid

    @staticmethod
    def get_style_state(
        is_invalid, is_modified, has_project_override, has_studio_override
    ):
        """Return stylesheet state by intered booleans."""
        if is_invalid:
            return "invalid"
        if is_modified:
            return "modified"
        if has_project_override:
            return "overridden"
        if has_studio_override:
            return "studio"
        return ""

    def hierarchical_style_update(self):
        raise NotImplementedError(
            "{} not implemented `hierarchical_style_update`".format(
                self.__class__.__name__
            )
        )

    def get_invalid(self):
        raise NotImplementedError(
            "{} not implemented `get_invalid`".format(
                self.__class__.__name__
            )
        )

    def _on_entity_change(self):
        """Not yet used."""
        print("{}: Warning missing `_on_entity_change` implementation".format(
            self.__class__.__name__
        ))

    def _discard_changes_action(self, menu, actions_mapping):
        # TODO use better condition as unsaved changes may be caused due to
        #   changes in schema.
        if not self.entity.can_trigger_discard_changes:
            return

        def discard_changes():
            with self.category_widget.working_state_context():
                self.ignore_input_changes.set_ignore(True)
                self.entity.discard_changes()
                self.ignore_input_changes.set_ignore(False)

        action = QtWidgets.QAction("Discard changes")
        actions_mapping[action] = discard_changes
        menu.addAction(action)

    def _add_to_studio_default(self, menu, actions_mapping):
        """Set values as studio overrides."""
        # Skip if not in studio overrides
        if not self.entity.can_trigger_add_to_studio_default:
            return

        def add_to_studio_default():
            with self.category_widget.working_state_context():
                self.entity.add_to_studio_default()
        action = QtWidgets.QAction("Add to studio default")
        actions_mapping[action] = add_to_studio_default
        menu.addAction(action)

    def _remove_from_studio_default_action(self, menu, actions_mapping):
        if not self.entity.can_trigger_remove_from_studio_default:
            return

        def remove_from_studio_default():
            with self.category_widget.working_state_context():
                self.ignore_input_changes.set_ignore(True)
                self.entity.remove_from_studio_default()
                self.ignore_input_changes.set_ignore(False)
        action = QtWidgets.QAction("Remove from studio default")
        actions_mapping[action] = remove_from_studio_default
        menu.addAction(action)

    def _add_to_project_override_action(self, menu, actions_mapping):
        if not self.entity.can_trigger_add_to_project_override:
            return

        def add_to_project_override():
            with self.category_widget.working_state_context():
                self.entity.add_to_project_override

        action = QtWidgets.QAction("Add to project override")
        actions_mapping[action] = add_to_project_override
        menu.addAction(action)

    def _remove_from_project_override_action(self, menu, actions_mapping):
        if not self.entity.can_trigger_remove_from_project_override:
            return

        def remove_from_project_override():
            with self.category_widget.working_state_context():
                self.ignore_input_changes.set_ignore(True)
                self.entity.remove_from_project_override()
                self.ignore_input_changes.set_ignore(False)

        action = QtWidgets.QAction("Remove from project override")
        actions_mapping[action] = remove_from_project_override
        menu.addAction(action)

    def _copy_value_actions(self, menu):
        def copy_value():
            mime_data = QtCore.QMimeData()

            if self.entity.is_dynamic_item or self.entity.is_in_dynamic_item:
                entity_path = None
            else:
                entity_path = "/".join(
                    [self.entity.root_key, self.entity.path]
                )

            value = self.entity.value
            # Copy for settings tool
            settings_data = {
                "root_key": self.entity.root_key,
                "value": value,
                "path": entity_path
            }
            settings_encoded_data = QtCore.QByteArray()
            settings_stream = QtCore.QDataStream(
                settings_encoded_data, QtCore.QIODevice.WriteOnly
            )
            settings_stream.writeQString(json.dumps(settings_data))
            mime_data.setData(
                "application/copy_settings_value", settings_encoded_data
            )

            # Copy as json
            json_encoded_data = None
            if isinstance(value, (dict, list)):
                json_encoded_data = QtCore.QByteArray()
                json_stream = QtCore.QDataStream(
                    json_encoded_data, QtCore.QIODevice.WriteOnly
                )
                json_stream.writeQString(json.dumps(value))

                mime_data.setData("application/json", json_encoded_data)

            # Copy as text
            if json_encoded_data is None:
                # Store value as string
                mime_data.setText(str(value))
            else:
                # Store data as json string
                mime_data.setText(json.dumps(value, indent=4))

            QtWidgets.QApplication.clipboard().setMimeData(mime_data)

        action = QtWidgets.QAction("Copy", menu)
        return [(action, copy_value)]

    def _paste_value_actions(self, menu):
        output = []
        # Allow paste of value only if were copied from this UI
        clipboard = QtWidgets.QApplication.clipboard()
        mime_data = clipboard.mimeData()
        mime_value = mime_data.data("application/copy_settings_value")
        # Skip if there is nothing to do
        if not mime_value:
            return output

        settings_stream = QtCore.QDataStream(
            mime_value, QtCore.QIODevice.ReadOnly
        )
        mime_data_value_str = settings_stream.readQString()
        mime_data_value = json.loads(mime_data_value_str)

        value = mime_data_value["value"]
        path = mime_data_value["path"]
        root_key = mime_data_value["root_key"]

        # Try to find matching entity to be able paste values to same spot
        # - entity can't by dynamic or in dynamic item
        # - must be in same root entity as source copy
        #       Can't copy system settings <-> project settings
        matching_entity = None
        if path and root_key == self.entity.root_key:
            try:
                matching_entity = self.entity.get_entity_from_path(path)
            except Exception:
                pass

        def _set_entity_value(_entity, _value):
            try:
                _entity.set(_value)
            except Exception:
                dialog = QtWidgets.QMessageBox(self)
                dialog.setWindowTitle("Value does not match settings schema")
                dialog.setIcon(QtWidgets.QMessageBox.Warning)
                dialog.setText((
                    "Pasted value does not seem to match schema of destination"
                    " settings entity."
                ))
                dialog.exec_()

        # Simple paste value method
        def paste_value():
            with self.category_widget.working_state_context():
                _set_entity_value(self.entity, value)

        action = QtWidgets.QAction("Paste", menu)
        output.append((action, paste_value))

        # Paste value to matching entity
        def paste_value_to_path():
            with self.category_widget.working_state_context():
                _set_entity_value(matching_entity, value)

        if matching_entity is not None:
            action = QtWidgets.QAction("Paste to same place", menu)
            output.append((action, paste_value_to_path))

        return output

    def _apply_values_from_project_action(self, menu, actions_mapping):
        for attr_name in ("project_name", "get_project_names"):
            if not hasattr(self.category_widget, attr_name):
                return

        if self.entity.is_dynamic_item or self.entity.is_in_dynamic_item:
            return

        current_project_name = self.category_widget.project_name
        project_names = []
        for project_name in self.category_widget.get_project_names():
            if project_name != current_project_name:
                project_names.append(project_name)

        if not project_names:
            return

        submenu = QtWidgets.QMenu("Apply values from", menu)

        for project_name in project_names:
            if project_name is None:
                project_name = DEFAULT_PROJECT_LABEL

            action = QtWidgets.QAction(project_name)
            submenu.addAction(action)
            actions_mapping[action] = functools.partial(
                self._apply_values_from_project,
                project_name
            )
        menu.addMenu(submenu)

    def _apply_values_from_project(self, project_name):
        with self.category_widget.working_state_context():
            try:
                path_keys = [
                    item
                    for item in self.entity.path.split("/")
                    if item
                ]
                entity = ProjectSettings(project_name)
                for key in path_keys:
                    entity = entity[key]
                self.entity.set(entity.value)

            except Exception:
                if project_name is None:
                    project_name = DEFAULT_PROJECT_LABEL

                # TODO better message
                title = "Applying values failed"
                msg = "Applying values from project \"{}\" failed.".format(
                    project_name
                )
                detail_msg = "".join(
                    traceback.format_exception(*sys.exc_info())
                )
                dialog = QtWidgets.QMessageBox(self)
                dialog.setWindowTitle(title)
                dialog.setIcon(QtWidgets.QMessageBox.Warning)
                dialog.setText(msg)
                dialog.setDetailedText(detail_msg)
                dialog.exec_()

    def show_actions_menu(self, event=None):
        if event and event.button() != QtCore.Qt.RightButton:
            return

        if not self.allow_actions:
            if event:
                return self.mouseReleaseEvent(event)
            return

        menu = QtWidgets.QMenu(self)

        actions_mapping = {}

        self._discard_changes_action(menu, actions_mapping)
        self._add_to_studio_default(menu, actions_mapping)
        self._remove_from_studio_default_action(menu, actions_mapping)
        self._add_to_project_override_action(menu, actions_mapping)
        self._remove_from_project_override_action(menu, actions_mapping)
        self._apply_values_from_project_action(menu, actions_mapping)

        ui_actions = []
        ui_actions.extend(self._copy_value_actions(menu))
        ui_actions.extend(self._paste_value_actions(menu))
        if ui_actions:
            menu.addSeparator()
            for action, callback in ui_actions:
                menu.addAction(action)
                actions_mapping[action] = callback

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()

    def focused_in(self):
        if self.entity is not None:
            self.set_path(self.entity.path)

    def mouseReleaseEvent(self, event):
        if self.allow_actions and event.button() == QtCore.Qt.RightButton:
            return self.show_actions_menu()

        focused_in = False
        if event.button() == QtCore.Qt.LeftButton:
            focused_in = True
            self.focused_in()

        result = super(BaseWidget, self).mouseReleaseEvent(event)
        if focused_in and not event.isAccepted():
            event.accept()
        return result


class InputWidget(BaseWidget):
    def __init__(self, *args, **kwargs):
        super(InputWidget, self).__init__(*args, **kwargs)

        # Input widgets have always timer available (but may not be used).
        self._value_change_timer = create_deffered_value_change_timer(
            self._on_value_change_timer
        )

    def start_value_timer(self):
        self._value_change_timer.start()

    def _on_value_change_timer(self):
        pass

    def create_ui(self):
        if self.entity.use_label_wrap:
            label = None
            self._create_label_wrap_ui()
        else:
            label = self.entity.label
            self.label_widget = None
            self.body_widget = None
            self.content_widget = self
            self.content_layout = self._create_layout(self)

        self._add_inputs_to_layout()

        self.entity_widget.add_widget_to_layout(self, label)

    def _create_label_wrap_ui(self):
        content_widget = QtWidgets.QWidget(self)
        content_widget.setObjectName("ContentWidget")

        content_widget.setProperty("content_state", "")
        content_layout_margins = (CHILD_OFFSET, 5, 0, 0)

        body_widget = ExpandingWidget(self.entity.label, self)
        label_widget = body_widget.label_widget
        body_widget.set_content_widget(content_widget)

        content_layout = self._create_layout(content_widget)
        content_layout.setContentsMargins(*content_layout_margins)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(body_widget)

        self.label_widget = label_widget
        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

    def _create_layout(self, parent_widget):
        layout = QtWidgets.QHBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        return layout

    def _add_inputs_to_layout(self):
        raise NotImplementedError(
            "Method `_add_inputs_to_layout` not implemented {}".format(
                self.__class__.__name__
            )
        )

    def make_sure_is_visible(self, path, scroll_to):
        if path:
            entity_path = self.entity.path
            if entity_path == path:
                self.set_focus(scroll_to)
                return True
        return False

    def update_style(self):
        has_unsaved_changes = self.entity.has_unsaved_changes
        if not has_unsaved_changes and self.entity.group_item:
            has_unsaved_changes = self.entity.group_item.has_unsaved_changes
        style_state = self.get_style_state(
            self.is_invalid,
            has_unsaved_changes,
            self.entity.has_project_override,
            self.entity.has_studio_override
        )
        if self._style_state == style_state:
            return

        self._style_state = style_state

        self.input_field.setProperty("input-state", style_state)
        self.input_field.style().polish(self.input_field)
        if self.label_widget:
            self.label_widget.setProperty("state", style_state)
            self.label_widget.style().polish(self.label_widget)

        if self.body_widget:
            if style_state:
                child_style_state = "child-{}".format(style_state)
            else:
                child_style_state = ""

            self.body_widget.side_line_widget.setProperty(
                "state", child_style_state
            )
            self.body_widget.side_line_widget.style().polish(
                self.body_widget.side_line_widget
            )

    @property
    def child_invalid(self):
        return self.is_invalid

    def hierarchical_style_update(self):
        self.update_style()

    def get_invalid(self):
        invalid = []
        if self.is_invalid:
            invalid.append(self)
        return invalid


class GUIWidget(BaseWidget):
    allow_actions = False
    separator_height = 2
    child_invalid = False

    def create_ui(self):
        entity_type = self.entity["type"]
        if entity_type == "label":
            self._create_label_ui()
        elif entity_type in ("separator", "splitter"):
            self._create_separator_ui()
        else:
            raise KeyError("Unknown GUI type {}".format(entity_type))

        self.entity_widget.add_widget_to_layout(self)

    def _create_label_ui(self):
        label = self.entity["label"]
        label_widget = QtWidgets.QLabel(label, self)
        label_widget.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        label_widget.setObjectName("SettingsLabel")
        label_widget.linkActivated.connect(self._on_link_activate)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(label_widget)

    def _create_separator_ui(self):
        splitter_item = QtWidgets.QWidget(self)
        splitter_item.setObjectName("Separator")
        splitter_item.setMinimumHeight(self.separator_height)
        splitter_item.setMaximumHeight(self.separator_height)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter_item)

    def _on_link_activate(self, url):
        if not url.startswith("settings://"):
            QtGui.QDesktopServices.openUrl(url)
            return

        path = url.replace("settings://", "")
        self.category_widget.go_to_fullpath(path)

    def set_entity_value(self):
        pass

    def hierarchical_style_update(self):
        pass

    def make_sure_is_visible(self, *args, **kwargs):
        return False

    def focused_in(self):
        pass

    def set_path(self, *args, **kwargs):
        pass

    def get_invalid(self):
        return []


class MockUpWidget(BaseWidget):
    allow_actions = False
    child_invalid = False

    def create_ui(self):
        label = "Mockup widget for entity {}".format(self.entity.path)
        label_widget = QtWidgets.QLabel(label, self)
        label_widget.setObjectName("SettingsLabel")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(label_widget)
        self.entity_widget.add_widget_to_layout(self)

    def set_entity_value(self):
        return

    def hierarchical_style_update(self):
        pass

    def get_invalid(self):
        return []
