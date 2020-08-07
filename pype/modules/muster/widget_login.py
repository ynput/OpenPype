import os
from Qt import QtCore, QtGui, QtWidgets
from avalon import style
from pype.api import resources


class MusterLogin(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 130

    loginSignal = QtCore.Signal(object, object, object)

    def __init__(self, main_parent=None, parent=None):

        super(MusterLogin, self).__init__()

        self.parent_widget = parent
        self.main_parent = main_parent

        # Icon
        if hasattr(parent, 'icon'):
            self.setWindowIcon(parent.icon)
        elif hasattr(parent, 'parent') and hasattr(parent.parent, 'icon'):
            self.setWindowIcon(parent.parent.icon)
        else:
            icon = QtGui.QIcon(resources.pype_icon_filepath())
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
        self.setWindowTitle('Muster login')

    def _main(self):
        self.main = QtWidgets.QVBoxLayout()
        self.main.setObjectName("main")

        self.form = QtWidgets.QFormLayout()
        self.form.setContentsMargins(10, 15, 10, 5)
        self.form.setObjectName("form")

        self.label_username = QtWidgets.QLabel("Username:")
        self.label_username.setFont(self.font)
        self.label_username.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.label_username.setTextFormat(QtCore.Qt.RichText)

        self.input_username = QtWidgets.QLineEdit()
        self.input_username.setEnabled(True)
        self.input_username.setFrame(True)
        self.input_username.setPlaceholderText(
            self._translate("main", "e.g. John Smith")
        )

        self.label_password = QtWidgets.QLabel("Password:")
        self.label_password.setFont(self.font)
        self.label_password.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.label_password.setTextFormat(QtCore.Qt.RichText)

        self.input_password = QtWidgets.QLineEdit()
        self.input_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.input_password.setEnabled(True)
        self.input_password.setFrame(True)
        self.input_password.setPlaceholderText(
            self._translate("main", "e.g. ********")
        )

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setFont(self.font)
        self.error_label.setStyleSheet('color: #FC6000')
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.form.addRow(self.label_username, self.input_username)
        self.form.addRow(self.label_password, self.input_password)
        self.form.addRow(self.error_label)

        self.btn_group = QtWidgets.QHBoxLayout()
        self.btn_group.addStretch(1)
        self.btn_group.setObjectName("btn_group")

        self.btn_ok = QtWidgets.QPushButton("Ok")
        self.btn_ok.clicked.connect(self.click_ok)

        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        QtWidgets.QShortcut(
            QtGui.QKeySequence(
                QtCore.Qt.Key_Escape), self).activated.connect(self.close)
        self.btn_cancel.clicked.connect(self.close)

        self.btn_group.addWidget(self.btn_ok)
        self.btn_group.addWidget(self.btn_cancel)

        self.main.addLayout(self.form)
        self.main.addLayout(self.btn_group)

        return self.main

    def keyPressEvent(self, key_event):
        if key_event.key() == QtCore.Qt.Key_Return:
            if self.input_username.hasFocus():
                self.input_password.setFocus()

            elif self.input_password.hasFocus() or self.btn_ok.hasFocus():
                self.click_ok()

            elif self.btn_cancel.hasFocus():
                self.close()
        else:
            super().keyPressEvent(key_event)

    def setError(self, msg):

        self.error_label.setText(msg)
        self.error_label.show()

    def invalid_input(self, entity):
        entity.setStyleSheet("border: 1px solid red;")

    def click_ok(self):
        # all what should happen - validations and saving into appsdir
        username = self.input_username.text()
        password = self.input_password.text()
        # TODO: more robust validation. Password can be empty in muster?
        if not username:
            self.setError("Username cannot be empty")
            self.invalid_input(self.input_username)
        try:
            self.save_credentials(username, password)
        except Exception as e:
            self.setError(
                "<b>Cannot get auth token:</b>\n<code>{}</code>".format(e))
        else:
            self._close_widget()

    def save_credentials(self, username, password):
        self.parent_widget.get_auth_token(username, password)

    def closeEvent(self, event):
        event.ignore()
        self._close_widget()

    def _close_widget(self):
        self.hide()
