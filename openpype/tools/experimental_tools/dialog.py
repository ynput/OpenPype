from Qt import QtWidgets

from openpype.style import (
    load_stylesheet,
    app_icon_path
)

from .tools_def import ExperimentalTools


class ToolButton(QtWidgets.QPushButton):
    triggered = QtCore.Signal(str)

    def __init__(self, identifier, *args, **kwargs):
        super(ExperimentalDialog, self).__init__(*args, **kwargs)
        self._identifier = identifier

        self.clicked.connect(self._on_click)

    def _on_click(self):
        self.triggered.emit(self._identifier)


class ExperimentalDialog(QtWidgets.QDialog):
    refresh_interval = 3000

    def __init__(self, parent=None):
        super(ExperimentalDialog, self).__init__(parent)
        self.setWindowTitle("OpenPype Experimental tools")
        self.setWindowIcon(app_icon_path())

        empty_label = QtWidgets.QLabel(
            "There are no experimental tools available.", self
        )
        content_widget = QtWidgets.QWidget(self)
        content_widget.setVisible(False)

        content_layout = QtWidgets.QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        experimental_tools = ExperimentalTools()
        buttons_by_tool_identifier = {}

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(empty_label)
        layout.addWidget(content_widget)

        refresh_timer = QtCore.QTimer()
        refresh_timer.setInterval(self.refresh_interval)
        refresh_timer.timeout.connect(self._on_refresh_timeout)

        self._empty_label = empty_label
        self._content_widget = content_widget
        self._content_layout = content_layout

        self._experimental_tools = experimental_tools
        self._buttons_by_tool_identifier = buttons_by_tool_identifier

        self._is_refreshing = False
        self._refresh_on_active = True
        self._window_is_active = False
        self._refresh_timer = refresh_timer

    def refresh(self):
        if self._is_refreshing:
            return
        self._is_refreshing = True

        self._experimental_tools.refresh_availability()

        buttons_to_remove = set(self._buttons_by_tool_identifier.keys())
        for idx, tool in enumerate(self._experimental_tools.experimental_tools):
            identifier = tool.identifier
            if identifier in buttons_to_remove:
                buttons_to_remove.remove(identifier)
                is_new = False
                button = self._buttons_by_tool_identifier[identifier]
            else:
                is_new = True
                button = ToolButton(identifier, self)
                button.triggered.connect(self._on_btn_trigger)
                self._buttons_by_tool_identifier[identifier] = button
                self._content_layout.insertWidget(idx, button)

            if button.text() != tool.label:
                button.setText(tool.label)

            if tool.enabled:
                button.setToolTip(tool.tooltip)

            elif is_new or button.isEnabled():
                button.setToolTip((
                    "You can enable this tool in local settings.
                    "\n\nOpenPype Tray > Settings > Experimental Tools"
                ))

        for identifier in buttons_to_remove:
            button = self._buttons_by_tool_identifier.pop(identifier)
            button.setVisible(False)
            idx = self._content_layout.indexOf(button)
            self._content_layout.takeAt(idx)
            button.deleteLater()

        self._empty_label.setVisible(not self._buttons_by_tool_identifier)

        self._is_refreshing = False

    def _on_btn_trigger(self, identifier):
        tool = self._experimental_tools.tools_by_identifier.get(identifier)
        if tool is not None:
            tool.execute()

    def showEvent(self, event):
        super(LauncherWindow, self).showEvent(event)

        if self._refresh_on_active:
            # Start/Restart timer
            self._refresh_timer.start()
            # Refresh
            self.refresh()

        elif not self._refresh_timer.isActive():
            self._refresh_timer.start()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.ActivationChange:
            self._window_is_active = self.isActiveWindow()
            if self._window_is_active and self._refresh_on_active:
                self._refresh_timer.start()
                self.refresh()

        super(LauncherWindow, self).changeEvent(event)

    def _on_refresh_timeout(self):
        # Stop timer if window is not visible
        if not self.isVisible():
            self._refresh_on_active = True
            self._refresh_timer.stop()

        # Skip refreshing if window is not active
        elif not self._window_is_active:
            self._refresh_on_active = True

        # Window is active and visible so we're refreshing buttons
        else:
            self.refresh()
