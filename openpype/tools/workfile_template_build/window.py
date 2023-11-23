from qtpy import QtWidgets

from openpype import style
from openpype.lib import Logger
from openpype.pipeline import legacy_io
from openpype.tools.attribute_defs import AttributeDefinitionsWidget


class WorkfileBuildPlaceholderDialog(QtWidgets.QDialog):
    def __init__(self, host, builder, parent=None):
        super(WorkfileBuildPlaceholderDialog, self).__init__(parent)
        self.setWindowTitle("Workfile Placeholder Manager")

        self._log = None

        self._first_show = True
        self._first_refreshed = False

        self._builder = builder
        self._host = host
        # Mode can be 0 (create) or 1 (update)
        # TODO write it a little bit better
        self._mode = 0
        self._update_item = None
        self._last_selected_plugin = None

        host_name = getattr(self._host, "name", None)
        if not host_name:
            host_name = legacy_io.Session.get("AVALON_APP") or "NA"
        self._host_name = host_name

        plugins_combo = QtWidgets.QComboBox(self)

        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        btns_widget = QtWidgets.QWidget(self)
        create_btn = QtWidgets.QPushButton("Create", btns_widget)
        save_btn = QtWidgets.QPushButton("Save", btns_widget)
        close_btn = QtWidgets.QPushButton("Close", btns_widget)

        create_btn.setVisible(False)
        save_btn.setVisible(False)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.addStretch(1)
        btns_layout.addWidget(create_btn, 0)
        btns_layout.addWidget(save_btn, 0)
        btns_layout.addWidget(close_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(plugins_combo, 0)
        main_layout.addWidget(content_widget, 1)
        main_layout.addWidget(btns_widget, 0)

        create_btn.clicked.connect(self._on_create_click)
        save_btn.clicked.connect(self._on_save_click)
        close_btn.clicked.connect(self._on_close_click)
        plugins_combo.currentIndexChanged.connect(self._on_plugin_change)

        self._attr_defs_widget = None
        self._plugins_combo = plugins_combo

        self._content_widget = content_widget
        self._content_layout = content_layout

        self._create_btn = create_btn
        self._save_btn = save_btn
        self._close_btn = close_btn

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def _clear_content_widget(self):
        while self._content_layout.count() > 0:
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                widget.deleteLater()

    def _add_message_to_content(self, message):
        msg_label = QtWidgets.QLabel(message, self._content_widget)
        self._content_layout.addWidget(msg_label, 0)
        self._content_layout.addStretch(1)

    def refresh(self):
        self._first_refreshed = True

        self._clear_content_widget()

        if not self._builder:
            self._add_message_to_content((
                "Host \"{}\" does not have implemented logic"
                " for template workfile build."
            ).format(self._host_name))
            self._update_ui_visibility()
            return

        placeholder_plugins = self._builder.placeholder_plugins

        if self._mode == 1:
            self._last_selected_plugin
            plugin = self._builder.placeholder_plugins.get(
                self._last_selected_plugin
            )
            self._create_option_widgets(
                plugin, self._update_item.to_dict()
            )
            self._update_ui_visibility()
            return

        if not placeholder_plugins:
            self._add_message_to_content((
                "Host \"{}\" does not have implemented plugins"
                " for template workfile build."
            ).format(self._host_name))
            self._update_ui_visibility()
            return

        last_selected_plugin = self._last_selected_plugin
        self._last_selected_plugin = None
        self._plugins_combo.clear()
        for identifier, plugin in placeholder_plugins.items():
            label = plugin.label or identifier
            self._plugins_combo.addItem(label, identifier)

        index = self._plugins_combo.findData(last_selected_plugin)
        if index < 0:
            index = 0
        self._plugins_combo.setCurrentIndex(index)
        self._on_plugin_change()

        self._update_ui_visibility()

    def set_create_mode(self):
        if self._mode == 0:
            return

        self._mode = 0
        self._update_item = None
        self.refresh()

    def set_update_mode(self, update_item):
        if self._mode == 1:
            return

        self._mode = 1
        self._update_item = update_item
        if update_item:
            self._last_selected_plugin = update_item.plugin.identifier
            self.refresh()
            return

        self._clear_content_widget()
        self._add_message_to_content((
            "Nothing to update."
            " (You maybe don't have selected placeholder.)"
        ))
        self._update_ui_visibility()

    def _create_option_widgets(self, plugin, options=None):
        self._clear_content_widget()
        attr_defs = plugin.get_placeholder_options(options)
        widget = AttributeDefinitionsWidget(attr_defs, self._content_widget)
        self._content_layout.addWidget(widget, 0)
        self._content_layout.addStretch(1)
        self._attr_defs_widget = widget
        self._last_selected_plugin = plugin.identifier

    def _update_ui_visibility(self):
        create_mode = self._mode == 0
        self._plugins_combo.setVisible(create_mode)

        if not self._builder:
            self._save_btn.setVisible(False)
            self._create_btn.setVisible(False)
            return

        save_enabled = not create_mode
        if save_enabled:
            save_enabled = self._update_item is not None
        self._save_btn.setVisible(save_enabled)
        self._create_btn.setVisible(create_mode)

    def _on_plugin_change(self):
        index = self._plugins_combo.currentIndex()
        plugin_identifier = self._plugins_combo.itemData(index)
        if plugin_identifier == self._last_selected_plugin:
            return

        plugin = self._builder.placeholder_plugins.get(plugin_identifier)
        self._create_option_widgets(plugin)

    def _on_save_click(self):
        options = self._attr_defs_widget.current_value()
        plugin = self._builder.placeholder_plugins.get(
            self._last_selected_plugin
        )
        # TODO much better error handling
        try:
            plugin.update_placeholder(self._update_item, options)
            self.accept()
        except Exception:
            self.log.warning("Something went wrong", exc_info=True)
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Something went wrong")
            dialog.setText("Something went wrong")
            dialog.exec_()

    def _on_create_click(self):
        options = self._attr_defs_widget.current_value()
        plugin = self._builder.placeholder_plugins.get(
            self._last_selected_plugin
        )
        # TODO much better error handling
        try:
            plugin.create_placeholder(options)
        except Exception:
            self.log.warning("Something went wrong", exc_info=True)
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Something went wrong")
            dialog.setText("Something went wrong")
            dialog.exec_()

    def _on_close_click(self):
        self.reject()

    def showEvent(self, event):
        super(WorkfileBuildPlaceholderDialog, self).showEvent(event)
        if not self._first_refreshed:
            self.refresh()

        if self._first_show:
            self._first_show = False
            self.setStyleSheet(style.load_stylesheet())
            self.resize(390, 450)
