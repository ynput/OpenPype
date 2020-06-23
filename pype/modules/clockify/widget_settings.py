import os
from Qt import QtCore, QtGui, QtWidgets
from avalon import style


class ClockifySettings(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 130

    loginSignal = QtCore.Signal(object, object, object)

    def __init__(self, main_parent=None, parent=None, optional=True):

        super(ClockifySettings, self).__init__()

        self.parent = parent
        self.main_parent = main_parent
        self.clockapi = parent.clockapi
        self.optional = optional
        self.validated = False

        # Icon
        if hasattr(parent, 'icon'):
            self.setWindowIcon(self.parent.icon)
        elif hasattr(parent, 'parent') and hasattr(parent.parent, 'icon'):
            self.setWindowIcon(self.parent.parent.icon)
        else:
            pype_setup = os.getenv('PYPE_SETUP_PATH')
            items = [pype_setup, "app", "resources", "icon.png"]
            fname = os.path.sep.join(items)
            icon = QtGui.QIcon(fname)
            self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )

        self._translate = QtCore.QCoreApplication.translate

        # Font
        self.font = QtGui.QFont()
        self.font.setFamily("DejaVu Sans Condensed")
        self.font.setPointSize(9)
        self.font.setBold(True)
        self.font.setWeight(50)
        self.font.setKerning(True)

        # Size setting
        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W+100, self.SIZE_H+100))
        self.setStyleSheet(style.load_stylesheet())

        self.setLayout(self._main())
        self.setWindowTitle('Clockify settings')

    def _main(self):
        self.main = QtWidgets.QVBoxLayout()
        self.main.setObjectName("main")

        self.form = QtWidgets.QFormLayout()
        self.form.setContentsMargins(10, 15, 10, 5)
        self.form.setObjectName("form")

        self.label_api_key = QtWidgets.QLabel("Clockify API key:")
        self.label_api_key.setFont(self.font)
        self.label_api_key.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.label_api_key.setTextFormat(QtCore.Qt.RichText)
        self.label_api_key.setObjectName("label_api_key")

        self.input_api_key = QtWidgets.QLineEdit()
        self.input_api_key.setEnabled(True)
        self.input_api_key.setFrame(True)
        self.input_api_key.setObjectName("input_api_key")
        self.input_api_key.setPlaceholderText(
            self._translate("main", "e.g. XX1XxXX2x3x4xXxx")
        )

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setFont(self.font)
        self.error_label.setTextFormat(QtCore.Qt.RichText)
        self.error_label.setObjectName("error_label")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.form.addRow(self.label_api_key, self.input_api_key)
        self.form.addRow(self.error_label)

        self.btn_group = QtWidgets.QHBoxLayout()
        self.btn_group.addStretch(1)
        self.btn_group.setObjectName("btn_group")

        self.btn_ok = QtWidgets.QPushButton("Ok")
        self.btn_ok.setToolTip('Sets Clockify API Key so can Start/Stop timer')
        self.btn_ok.clicked.connect(self.click_ok)

        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        cancel_tooltip = 'Application won\'t start'
        if self.optional:
            cancel_tooltip = 'Close this window'
        self.btn_cancel.setToolTip(cancel_tooltip)
        self.btn_cancel.clicked.connect(self._close_widget)

        self.btn_group.addWidget(self.btn_ok)
        self.btn_group.addWidget(self.btn_cancel)

        self.main.addLayout(self.form)
        self.main.addLayout(self.btn_group)

        return self.main

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
