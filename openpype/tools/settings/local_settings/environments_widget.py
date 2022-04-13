from Qt import QtWidgets

from openpype.tools.utils import PlaceholderLineEdit


class LocalEnvironmentsWidgets(QtWidgets.QWidget):
    def __init__(self, system_settings_entity, parent):
        super(LocalEnvironmentsWidgets, self).__init__(parent)

        self._widgets_by_env_key = {}
        self.system_settings_entity = system_settings_entity

        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QGridLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._layout = layout
        self._content_layout = content_layout
        self._content_widget = content_widget

    def _clear_layout(self, layout):
        while layout.count() > 0:
            item = layout.itemAt(0)
            widget = item.widget()
            layout.removeItem(item)
            if widget is not None:
                widget.setVisible(False)
                widget.deleteLater()

    def _reset_env_widgets(self):
        self._clear_layout(self._content_layout)
        self._clear_layout(self._layout)

        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QGridLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        white_list_entity = (
            self.system_settings_entity["general"]["local_env_white_list"]
        )
        row = -1
        for row, item in enumerate(white_list_entity):
            key = item.value
            label_widget = QtWidgets.QLabel(key, self)
            input_widget = PlaceholderLineEdit(self)
            input_widget.setPlaceholderText("< Keep studio value >")

            content_layout.addWidget(label_widget, row, 0)
            content_layout.addWidget(input_widget, row, 1)

            self._widgets_by_env_key[key] = input_widget

        if row < 0:
            label_widget = QtWidgets.QLabel(
                (
                    "Your studio does not allow to change"
                    " Environment variables locally."
                ),
                self
            )
            content_layout.addWidget(label_widget, 0, 0)
            content_layout.setColumnStretch(0, 1)

        else:
            content_layout.setColumnStretch(0, 0)
            content_layout.setColumnStretch(1, 1)

        self._layout.addWidget(content_widget, 1)

        self._content_layout = content_layout
        self._content_widget = content_widget

    def update_local_settings(self, value):
        if not value:
            value = {}

        self._reset_env_widgets()

        for env_key, widget in self._widgets_by_env_key.items():
            env_value = value.get(env_key) or ""
            widget.setText(env_value)

    def settings_value(self):
        output = {}
        for env_key, widget in self._widgets_by_env_key.items():
            value = widget.text()
            if value:
                output[env_key] = value
        if not output:
            return None
        return output
