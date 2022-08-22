from Qt import QtWidgets, QtCore

from openpype.tools.utils.delegates import pretty_date


class BaseInfoDialog(QtWidgets.QDialog):
    width = 600
    height = 400

    def __init__(self, message, title, info_obj, parent=None):
        super(BaseInfoDialog, self).__init__(parent)
        self._result = 0
        self._info_obj = info_obj

        self.setWindowTitle(title)

        message_label = QtWidgets.QLabel(message, self)
        message_label.setWordWrap(True)

        separator_widget_1 = QtWidgets.QFrame(self)
        separator_widget_2 = QtWidgets.QFrame(self)
        for separator_widget in (
            separator_widget_1,
            separator_widget_2
        ):
            separator_widget.setObjectName("Separator")
            separator_widget.setMinimumHeight(1)
            separator_widget.setMaximumHeight(1)

        other_information = QtWidgets.QWidget(self)
        other_information_layout = QtWidgets.QFormLayout(other_information)
        other_information_layout.setContentsMargins(0, 0, 0, 0)
        for label, value in (
            ("Username", info_obj.username),
            ("Host name", info_obj.hostname),
            ("Host IP", info_obj.hostip),
            ("System name", info_obj.system_name),
            ("Local ID", info_obj.local_id),
        ):
            other_information_layout.addRow(
                label,
                QtWidgets.QLabel(value, other_information)
            )

        timestamp_label = QtWidgets.QLabel(
            pretty_date(info_obj.timestamp_obj), other_information
        )
        other_information_layout.addRow("Time", timestamp_label)

        footer_widget = QtWidgets.QWidget(self)
        buttons_widget = QtWidgets.QWidget(footer_widget)

        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons = self.get_buttons(buttons_widget)
        for button in buttons:
            buttons_layout.addWidget(button, 1)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(buttons_widget, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(message_label, 0)
        layout.addWidget(separator_widget_1, 0)
        layout.addStretch(1)
        layout.addWidget(other_information, 0, QtCore.Qt.AlignHCenter)
        layout.addStretch(1)
        layout.addWidget(separator_widget_2, 0)
        layout.addWidget(footer_widget, 0)

        timestamp_timer = QtCore.QTimer()
        timestamp_timer.setInterval(1000)
        timestamp_timer.timeout.connect(self._on_timestamp_timer)

        self._timestamp_label = timestamp_label
        self._timestamp_timer = timestamp_timer

    def showEvent(self, event):
        super(BaseInfoDialog, self).showEvent(event)
        self._timestamp_timer.start()
        self.resize(self.width, self.height)

    def closeEvent(self, event):
        self._timestamp_timer.stop()
        super(BaseInfoDialog, self).closeEvent(event)

    def _on_timestamp_timer(self):
        self._timestamp_label.setText(
            pretty_date(self._info_obj.timestamp_obj)
        )

    def result(self):
        return self._result

    def get_buttons(self, parent):
        return []


class SettingsUIOpenedElsewhere(BaseInfoDialog):
    def __init__(self, info_obj, parent=None):
        title = "Someone else has opened Settings UI"
        message = (
            "Someone else has opened Settings UI which could cause data loss."
            " Please contact the person on the other side."
            "<br/><br/>You can continue in <b>view-only mode</b>."
            " All changes in view mode will be lost."
            "<br/><br/>You can <b>take control</b> which will cause that"
            " all changes of settings on the other side will be lost.<br/>"
        )
        super(SettingsUIOpenedElsewhere, self).__init__(
            message, title, info_obj, parent
        )

    def _on_take_control(self):
        self._result = 1
        self.close()

    def _on_view_mode(self):
        self._result = 0
        self.close()

    def get_buttons(self, parent):
        take_control_btn = QtWidgets.QPushButton(
            "Take control", parent
        )
        view_mode_btn = QtWidgets.QPushButton(
            "View only", parent
        )

        take_control_btn.clicked.connect(self._on_take_control)
        view_mode_btn.clicked.connect(self._on_view_mode)

        return [
            take_control_btn,
            view_mode_btn
        ]


class SettingsLastSavedChanged(BaseInfoDialog):
    width = 500
    height = 300

    def __init__(self, info_obj, parent=None):
        title = "Settings has changed"
        message = (
            "Settings has changed while you had opened this settings session."
            "<br/><br/>It is <b>recommended to refresh settings</b>"
            " and re-apply changes in the new session."
        )
        super(SettingsLastSavedChanged, self).__init__(
            message, title, info_obj, parent
        )

    def _on_save(self):
        self._result = 1
        self.close()

    def _on_close(self):
        self._result = 0
        self.close()

    def get_buttons(self, parent):
        close_btn = QtWidgets.QPushButton(
            "Close", parent
        )
        save_btn = QtWidgets.QPushButton(
            "Save anyway", parent
        )

        close_btn.clicked.connect(self._on_close)
        save_btn.clicked.connect(self._on_save)

        return [
            close_btn,
            save_btn
        ]


class SettingsControlTaken(BaseInfoDialog):
    width = 500
    height = 300

    def __init__(self, info_obj, parent=None):
        title = "Settings control taken"
        message = (
            "Someone took control over your settings."
            "<br/><br/>It is not possible to save changes of currently"
            " opened session. Copy changes you want to keep and hit refresh."
        )
        super(SettingsControlTaken, self).__init__(
            message, title, info_obj, parent
        )

    def _on_confirm(self):
        self.close()

    def get_buttons(self, parent):
        confirm_btn = QtWidgets.QPushButton("Understand", parent)
        confirm_btn.clicked.connect(self._on_confirm)
        return [confirm_btn]
