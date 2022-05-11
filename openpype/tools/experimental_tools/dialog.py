from Qt import QtWidgets, QtCore, QtGui

from openpype.style import (
    load_stylesheet,
    app_icon_path
)

from .tools_def import ExperimentalTools


class ToolButton(QtWidgets.QPushButton):
    triggered = QtCore.Signal(str)

    def __init__(self, identifier, *args, **kwargs):
        super(ToolButton, self).__init__(*args, **kwargs)
        self._identifier = identifier

        self.clicked.connect(self._on_click)

    def _on_click(self):
        self.triggered.emit(self._identifier)


class ExperimentalToolsDialog(QtWidgets.QDialog):
    refresh_interval = 3000

    def __init__(self, parent=None):
        super(ExperimentalToolsDialog, self).__init__(parent)
        self.setWindowTitle("OpenPype Experimental tools")
        icon = QtGui.QIcon(app_icon_path())
        self.setWindowIcon(icon)
        self.setStyleSheet(load_stylesheet())

        # Widgets for cases there are not available experimental tools
        empty_widget = QtWidgets.QWidget(self)

        empty_label = QtWidgets.QLabel(
            "There are no experimental tools available...", empty_widget
        )

        empty_btns_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("OK", empty_widget)

        empty_btns_layout.setContentsMargins(0, 0, 0, 0)
        empty_btns_layout.addStretch(1)
        empty_btns_layout.addWidget(ok_btn, 0)

        empty_layout = QtWidgets.QVBoxLayout(empty_widget)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.addWidget(empty_label)
        empty_layout.addStretch(1)
        empty_layout.addLayout(empty_btns_layout)

        # Content of Experimental tools

        # Layout where buttons are added
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Separator line
        separator_widget = QtWidgets.QWidget(self)
        separator_widget.setObjectName("Separator")
        separator_widget.setMinimumHeight(2)
        separator_widget.setMaximumHeight(2)

        # Label describing how to turn off tools
        tool_btns_widget = QtWidgets.QWidget(self)
        tool_btns_label = QtWidgets.QLabel(
            (
                "You can enable these features in"
                "<br><b>OpenPype tray -> Settings -> Experimental tools</b>"
            ),
            tool_btns_widget
        )
        tool_btns_label.setAlignment(QtCore.Qt.AlignCenter)

        tool_btns_layout = QtWidgets.QVBoxLayout(tool_btns_widget)
        tool_btns_layout.setContentsMargins(0, 0, 0, 0)
        tool_btns_layout.addLayout(content_layout)
        tool_btns_layout.addStretch(1)
        tool_btns_layout.addWidget(separator_widget, 0)
        tool_btns_layout.addWidget(tool_btns_label, 0)

        experimental_tools = ExperimentalTools(
            parent_widget=parent, refresh=False
        )

        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(empty_widget, 1)
        layout.addWidget(tool_btns_widget, 1)

        refresh_timer = QtCore.QTimer()
        refresh_timer.setInterval(self.refresh_interval)
        refresh_timer.timeout.connect(self._on_refresh_timeout)

        ok_btn.clicked.connect(self._on_ok_click)

        self._empty_widget = empty_widget
        self._tool_btns_widget = tool_btns_widget
        self._content_layout = content_layout

        self._experimental_tools = experimental_tools
        self._buttons_by_tool_identifier = {}

        self._refresh_timer = refresh_timer

        # Is dialog first shown
        self._first_show = True
        # Trigger refresh when window gets activity
        self._refresh_on_active = True
        # Is window active
        self._window_is_active = False

    def refresh(self):
        self._experimental_tools.refresh_availability()

        buttons_to_remove = set(self._buttons_by_tool_identifier.keys())
        tools = self._experimental_tools.get_tools_for_host()
        for idx, tool in enumerate(tools):
            identifier = tool.identifier
            if identifier in buttons_to_remove:
                buttons_to_remove.remove(identifier)
                is_new = False
                button = self._buttons_by_tool_identifier[identifier]
            else:
                is_new = True
                button = ToolButton(identifier, self._tool_btns_widget)
                button.triggered.connect(self._on_btn_trigger)
                self._buttons_by_tool_identifier[identifier] = button
                self._content_layout.insertWidget(idx, button)

            if button.text() != tool.label:
                button.setText(tool.label)

            if tool.enabled:
                button.setToolTip(tool.tooltip)

            elif is_new or button.isEnabled():
                button.setToolTip((
                    "You can enable this tool in local settings."
                    "\n\nOpenPype Tray > Settings > Experimental Tools"
                ))

            if tool.enabled != button.isEnabled():
                button.setEnabled(tool.enabled)

        for identifier in buttons_to_remove:
            button = self._buttons_by_tool_identifier.pop(identifier)
            button.setVisible(False)
            idx = self._content_layout.indexOf(button)
            self._content_layout.takeAt(idx)
            button.deleteLater()

        self._set_visibility()

    def _is_content_visible(self):
        return len(self._buttons_by_tool_identifier) > 0

    def _set_visibility(self):
        content_visible = self._is_content_visible()
        self._tool_btns_widget.setVisible(content_visible)
        self._empty_widget.setVisible(not content_visible)

    def _on_ok_click(self):
        self.close()

    def _on_btn_trigger(self, identifier):
        tool = self._experimental_tools.tools_by_identifier.get(identifier)
        if tool is not None:
            tool.execute()

    def showEvent(self, event):
        super(ExperimentalToolsDialog, self).showEvent(event)

        if self._refresh_on_active:
            # Start/Restart timer
            self._refresh_timer.start()
            # Refresh
            self.refresh()

        elif not self._refresh_timer.isActive():
            self._refresh_timer.start()

        if self._first_show:
            self._first_show = False
            # Set stylesheet
            self.setStyleSheet(load_stylesheet())
            # Resize dialog if there is not content
            if not self._is_content_visible():
                size = self.size()
                size.setWidth(size.width() + size.width() / 3)
                self.resize(size)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.ActivationChange:
            self._window_is_active = self.isActiveWindow()
            if self._window_is_active and self._refresh_on_active:
                self._refresh_timer.start()
                self.refresh()

        super(ExperimentalToolsDialog, self).changeEvent(event)

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
