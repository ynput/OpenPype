from Qt import QtWidgets, QtGui, QtCore
from pype.settings.entities import OverrideState


class BaseWidget(QtWidgets.QWidget):
    allow_actions = True

    def __init__(self, entity, entity_widget):
        self.entity = entity
        self.entity_widget = entity_widget

        self.trigger_hierarchical_style_update = (
            self.entity_widget.trigger_hierarchical_style_update
        )
        self.ignore_input_changes = entity_widget.ignore_input_changes
        self.create_ui_for_entity = entity_widget.create_ui_for_entity

        self._is_invalid = False
        self._style_state = None

        super(BaseWidget, self).__init__(entity_widget.content_widget)

        self.entity.on_change_callbacks.append(self._on_entity_change)

        self.label_widget = None
        self.create_ui()

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
            return "overriden"
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
        print("{}: Wraning missing `_on_entity_change` implementation".format(
            self.__class__.__name__
        ))

    def _discard_changes_action(self, menu, actions_mapping):
        # TODO use better condition as unsaved changes may be caused due to
        #   changes in schema.
        if not self.entity.has_unsaved_changes:
            return

        def discard_changes():
            self.ignore_input_changes.set_ignore(True)
            self.entity.discard_changes()
            self.ignore_input_changes.set_ignore(False)

        action = QtWidgets.QAction("Discard changes")
        actions_mapping[action] = discard_changes
        menu.addAction(action)

    def _set_project_override_action(self, menu, actions_mapping):
        # Show only when project overrides are set
        if self.entity.override_state < OverrideState.PROJECT:
            return

        # Do not show on items under group item
        if self.entity.group_item:
            return

        # Skip if already is marked to save project overrides
        if self.entity.is_group and self.entity.child_has_studio_override:
            return

        action = QtWidgets.QAction("Set project override")
        actions_mapping[action] = self.entity.set_as_overriden
        menu.addAction(action)

    def _reset_to_pype_default_action(self, menu, actions_mapping):
        if self.entity.override_state is not OverrideState.STUDIO:
            return

        if (
            self.entity.has_studio_override
            or self.entity.child_has_studio_override
        ):
            def reset_to_pype_default():
                self.ignore_input_changes.set_ignore(True)
                self.entity.reset_to_pype_default()
                self.ignore_input_changes.set_ignore(False)
            action = QtWidgets.QAction("Reset to pype default")
            actions_mapping[action] = reset_to_pype_default
            menu.addAction(action)

    def _set_studio_default(self, menu, actions_mapping):
        """Set values as studio overrides."""
        # Skip if not in studio overrides
        if self.entity.override_state is not OverrideState.STUDIO:
            return

        # Skip if entity is under group
        if self.entity.group_item:
            return

        # Skip if is group and any children is already marked with studio
        #   overrides
        if self.entity.is_group and self.entity.child_has_studio_override:
            return

        # TODO better label
        action = QtWidgets.QAction("Set studio default")
        actions_mapping[action] = self.entity.set_studio_default
        menu.addAction(action)

    def _remove_project_override_action(self, menu, actions_mapping):
        # Dynamic items can't have these actions
        if self.entity.is_dynamic_item or self.entity.is_in_dynamic_item:
            return

        if self.entity.is_group:
            if not self.entity.child_has_project_override:
                return

        elif self.entity.group_item:
            if not self.entity.group_item.child_has_project_override:
                return

        elif not self.entity.child_has_project_override:
            return

        # TODO better label
        action = QtWidgets.QAction("Remove project override")
        actions_mapping[action] = self.entity.remove_overrides
        menu.addAction(action)

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
        self._set_project_override_action(menu, actions_mapping)
        self._reset_to_pype_default_action(menu, actions_mapping)
        self._set_studio_default(menu, actions_mapping)
        self._remove_project_override_action(menu, actions_mapping)

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()

    def mouseReleaseEvent(self, event):
        if self.allow_actions and event.button() == QtCore.Qt.RightButton:
            return self.show_actions_menu()

        return super(BaseWidget, self).mouseReleaseEvent(event)


class InputWidget(BaseWidget):
    def update_style(self):
        has_unsaved_changes = self.entity.has_unsaved_changes
        if not has_unsaved_changes and self.entity.group_item:
            has_unsaved_changes = self.entity.group_item.has_unsaved_changes
        state = self.get_style_state(
            self.is_invalid,
            has_unsaved_changes,
            self.entity.has_project_override,
            self.entity.has_studio_override
        )
        if self._style_state == state:
            return

        self._style_state = state

        self.input_field.setProperty("input-state", state)
        self.input_field.style().polish(self.input_field)
        if self.label_widget:
            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

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
        self.setObjectName("LabelWidget")

        label = self.entity["label"]
        label_widget = QtWidgets.QLabel(label, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(label_widget)

    def _create_separator_ui(self):
        splitter_item = QtWidgets.QWidget(self)
        splitter_item.setObjectName("SplitterItem")
        splitter_item.setMinimumHeight(self.separator_height)
        splitter_item.setMaximumHeight(self.separator_height)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter_item)

    def set_entity_value(self):
        return

    def hierarchical_style_update(self):
        pass

    def get_invalid(self):
        return []
