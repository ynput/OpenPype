from Qt import QtCore, QtGui, QtWidgets
from openpype import resources, style


class MessageWidget(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 130

    closed = QtCore.Signal()

    def __init__(self, messages, title):
        super(MessageWidget, self).__init__()

        # Icon
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )

        # Size setting
        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W+100, self.SIZE_H+100))

        # Style
        self.setStyleSheet(style.load_stylesheet())

        self.setLayout(self._ui_layout(messages))
        self.setWindowTitle(title)

    def _ui_layout(self, messages):
        if not messages:
            messages = ["*Misssing messages (This is a bug)*", ]

        elif not isinstance(messages, (tuple, list)):
            messages = [messages, ]

        main_layout = QtWidgets.QVBoxLayout(self)

        labels = []
        for message in messages:
            label = QtWidgets.QLabel(message)
            label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            label.setTextFormat(QtCore.Qt.RichText)
            label.setWordWrap(True)

            labels.append(label)
            main_layout.addWidget(label)

        btn_close = QtWidgets.QPushButton("Close")
        btn_close.setToolTip('Close this window')
        btn_close.clicked.connect(self.on_close_clicked)

        btn_group = QtWidgets.QHBoxLayout()
        btn_group.addStretch(1)
        btn_group.addWidget(btn_close)

        main_layout.addLayout(btn_group)

        self.labels = labels
        self.btn_group = btn_group
        self.btn_close = btn_close
        self.main_layout = main_layout

        return main_layout

    def on_close_clicked(self):
        self.close()

    def close(self, *args, **kwargs):
        self.closed.emit()
        super(MessageWidget, self).close(*args, **kwargs)


class ClockifySettings(QtWidgets.QWidget):
    SIZE_W = 300
    SIZE_H = 130

    loginSignal = QtCore.Signal(object, object, object)

    def __init__(self, clockapi, optional=True):
        super(ClockifySettings, self).__init__()

        self.clockapi = clockapi
        self.optional = optional
        self.validated = False

        # Icon
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)

        self.setWindowTitle("Clockify settings")
        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )

        # Size setting
        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W+100, self.SIZE_H+100))
        self.setStyleSheet(style.load_stylesheet())

        self._ui_init()

    def _ui_init(self):
        label_api_key = QtWidgets.QLabel("Clockify API key:")

        input_api_key = QtWidgets.QLineEdit()
        input_api_key.setFrame(True)
        input_api_key.setPlaceholderText("e.g. XX1XxXX2x3x4xXxx")

        error_label = QtWidgets.QLabel("")
        error_label.setTextFormat(QtCore.Qt.RichText)
        error_label.setWordWrap(True)
        error_label.hide()

        form_layout = QtWidgets.QFormLayout()
        form_layout.setContentsMargins(10, 15, 10, 5)
        form_layout.addRow(label_api_key, input_api_key)
        form_layout.addRow(error_label)

        btn_ok = QtWidgets.QPushButton("Ok")
        btn_ok.setToolTip('Sets Clockify API Key so can Start/Stop timer')

        btn_cancel = QtWidgets.QPushButton("Cancel")
        cancel_tooltip = 'Application won\'t start'
        if self.optional:
            cancel_tooltip = 'Close this window'
        btn_cancel.setToolTip(cancel_tooltip)

        btn_group = QtWidgets.QHBoxLayout()
        btn_group.addStretch(1)
        btn_group.addWidget(btn_ok)
        btn_group.addWidget(btn_cancel)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_group)

        btn_ok.clicked.connect(self.click_ok)
        btn_cancel.clicked.connect(self._close_widget)

        self.label_api_key = label_api_key
        self.input_api_key = input_api_key
        self.error_label = error_label

        self.btn_ok = btn_ok
        self.btn_cancel = btn_cancel

    def setError(self, msg):
        self.error_label.setText(msg)
        self.error_label.show()

    def invalid_input(self, entity):
        entity.setStyleSheet("border: 1px solid red;")

    def click_ok(self):
        api_key = self.input_api_key.text().strip()
        if self.optional is True and api_key == '':
            self.clockapi.save_api_key(None)
            self.clockapi.set_api(api_key)
            self.validated = False
            self._close_widget()
            return

        validation = self.clockapi.validate_api_key(api_key)

        if validation:
            self.clockapi.save_api_key(api_key)
            self.clockapi.set_api(api_key)
            self.validated = True
            self._close_widget()
        else:
            self.invalid_input(self.input_api_key)
            self.validated = False
            self.setError(
                "Entered invalid API key"
            )

    def showEvent(self, event):
        super(ClockifySettings, self).showEvent(event)

        # Make btns same width
        max_width = max(
            self.btn_ok.sizeHint().width(),
            self.btn_cancel.sizeHint().width()
        )
        self.btn_ok.setMinimumWidth(max_width)
        self.btn_cancel.setMinimumWidth(max_width)

    def closeEvent(self, event):
        if self.optional is True:
            event.ignore()
            self._close_widget()
        else:
            self.validated = False

    def _close_widget(self):
        if self.optional is True:
            self.hide()
        else:
            self.close()
