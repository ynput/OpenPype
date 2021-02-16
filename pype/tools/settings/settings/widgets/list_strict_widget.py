class ListStrictWidget(QtWidgets.QWidget, InputObject):
    value_changed = QtCore.Signal(object)
    _default_input_value = None
    valid_value_types = (list, )

    def __init__(
        self, schema_data, parent, as_widget=False, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(ListStrictWidget, self).__init__(parent_widget)
        self.setObjectName("ListStrictWidget")

        self.initial_attributes(schema_data, parent, as_widget)

        self.is_horizontal = schema_data.get("horizontal", True)
        self.object_types = self.schema_data["object_types"]

        self.input_fields = []

    def create_ui(self, label_widget=None):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setSpacing(5)

        if not self.as_widget and not label_widget:
            label = self.schema_data.get("label")
            if label:
                label_widget = QtWidgets.QLabel(label, self)
                layout.addWidget(label_widget, alignment=QtCore.Qt.AlignTop)
            elif self._is_group:
                raise KeyError((
                    "Schema item must contain \"label\" if `is_group` is True"
                    " to be able visualize changes and show actions."
                ))

        self.label_widget = label_widget

        self._add_children(layout)

    def _add_children(self, layout):
        inputs_widget = QtWidgets.QWidget(self)
        inputs_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        layout.addWidget(inputs_widget)

        if self.is_horizontal:
            inputs_layout = QtWidgets.QHBoxLayout(inputs_widget)
        else:
            inputs_layout = QtWidgets.QGridLayout(inputs_widget)

        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(3)

        self.inputs_widget = inputs_widget
        self.inputs_layout = inputs_layout

        children_item_mapping = []
        for child_configuration in self.object_types:
            item_widget = ListItem(
                child_configuration, self, self.inputs_widget, is_strict=True
            )

            self.input_fields.append(item_widget)
            item_widget.value_changed.connect(self._on_value_change)

            label = child_configuration.get("label")
            label_widget = None
            if label:
                label_widget = QtWidgets.QLabel(label, self)

            children_item_mapping.append((label_widget, item_widget))

        if self.is_horizontal:
            self._add_children_horizontally(children_item_mapping)
        else:
            self._add_children_vertically(children_item_mapping)

        self.updateGeometry()

    def _add_children_vertically(self, children_item_mapping):
        any_has_label = False
        for item_mapping in children_item_mapping:
            if item_mapping[0]:
                any_has_label = True
                break

        row = self.inputs_layout.count()
        if not any_has_label:
            self.inputs_layout.setColumnStretch(1, 1)
            for item_mapping in children_item_mapping:
                item_widget = item_mapping[1]
                self.inputs_layout.addWidget(item_widget, row, 0, 1, 1)

                spacer_widget = QtWidgets.QWidget(self.inputs_widget)
                self.inputs_layout.addWidget(spacer_widget, row, 1, 1, 1)
                row += 1

        else:
            self.inputs_layout.setColumnStretch(2, 1)
            for label_widget, item_widget in children_item_mapping:
                self.inputs_layout.addWidget(
                    label_widget, row, 0, 1, 1,
                    alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignTop
                )
                self.inputs_layout.addWidget(item_widget, row, 1, 1, 1)

                spacer_widget = QtWidgets.QWidget(self.inputs_widget)
                self.inputs_layout.addWidget(spacer_widget, row, 2, 1, 1)
                row += 1

    def _add_children_horizontally(self, children_item_mapping):
        for label_widget, item_widget in children_item_mapping:
            if label_widget:
                self.inputs_layout.addWidget(label_widget, 0)
            self.inputs_layout.addWidget(item_widget, 0)

        spacer_widget = QtWidgets.QWidget(self.inputs_widget)
        self.inputs_layout.addWidget(spacer_widget, 1)

    @property
    def default_input_value(self):
        if self._default_input_value is None:
            self.set_value(NOT_SET)
            self._default_input_value = self.item_value()
        return self._default_input_value

    def set_value(self, value):
        if self._is_overriden:
            method_name = "apply_overrides"
        elif not self._has_studio_override:
            method_name = "update_default_values"
        else:
            method_name = "update_studio_values"

        for idx, input_field in enumerate(self.input_fields):
            if value is NOT_SET:
                _value = value
            else:
                if idx > len(value) - 1:
                    _value = NOT_SET
                else:
                    _value = value[idx]
            _method = getattr(input_field, method_name)
            _method(_value)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        if not self.label_widget:
            return

        state = self._style_state()

        if self._state == state:
            return

        self._state = state
        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        output = []
        for item in self.input_fields:
            output.append(item.config_value())
        return output
