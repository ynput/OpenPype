from Qt import QtWidgets


class BaseWidget(QtWidgets.QWidget):
    def __init__(self, entity, entity_widget):
        self.entity = entity
        self.entity_widget = entity_widget

        self.ignore_input_changes = entity_widget.ignore_input_changes
        self.create_ui_for_entity = entity_widget.create_ui_for_entity

        self.is_invalid = False
        self._style_state = None

        super(BaseWidget, self).__init__(entity_widget.content_widget)

        self.entity.on_change_callbacks.append(self._on_entity_change)

        self.label_widget = None
        self.create_ui()

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

    def show_actions_menu(self, event):
        print("Show actions for {}".format(self.entity.path))


class InputWidget(BaseWidget):
    def update_style(self):
        state = self.get_style_state(
            self.is_invalid,
            self.entity.has_unsaved_changes,
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

    def _on_entity_change(self):
        pass

    def hierarchical_style_update(self):
        pass

    def get_invalid(self):
        return []
