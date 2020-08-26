import os
import requests
from avalon import style
from pype.modules.ftrack import credentials
from . import login_tools
from pype.api import resources
from Qt import QtCore, QtGui, QtWidgets


class CredentialsDialog(QtWidgets.QDialog):
    SIZE_W = 300
    SIZE_H = 230

    login_changed = QtCore.Signal()
    logout_signal = QtCore.Signal()

    def __init__(self, parent=None):
        super(CredentialsDialog, self).__init__(parent)

        self.setWindowTitle("Pype - Ftrack Login")

        self._login_server_thread = None
        self._is_logged = False
        self._in_advance_mode = False

        icon = QtGui.QIcon(resources.pype_icon_filepath())
        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )

        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W + 100, self.SIZE_H + 100))
        self.setStyleSheet(style.load_stylesheet())

        self.login_changed.connect(self._on_login)

        self.ui_init()

    def ui_init(self):
        self.ftsite_label = QtWidgets.QLabel("Ftrack URL:")
        self.user_label = QtWidgets.QLabel("Username:")
        self.api_label = QtWidgets.QLabel("API Key:")

        self.ftsite_input = QtWidgets.QLineEdit()
        self.ftsite_input.setReadOnly(True)
        self.ftsite_input.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))

        self.user_input = QtWidgets.QLineEdit()
        self.user_input.setPlaceholderText("user.name")
        self.user_input.textChanged.connect(self._user_changed)

        self.api_input = QtWidgets.QLineEdit()
        self.api_input.setPlaceholderText(
            "e.g. xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        )
        self.api_input.textChanged.connect(self._api_changed)

        input_layout = QtWidgets.QFormLayout()
        input_layout.setContentsMargins(10, 15, 10, 5)

        input_layout.addRow(self.ftsite_label, self.ftsite_input)
        input_layout.addRow(self.user_label, self.user_input)
        input_layout.addRow(self.api_label, self.api_input)

        self.btn_advanced = QtWidgets.QPushButton("Advanced")
        self.btn_advanced.clicked.connect(self._on_advanced_clicked)

        self.btn_simple = QtWidgets.QPushButton("Simple")
        self.btn_simple.clicked.connect(self._on_simple_clicked)

        self.btn_login = QtWidgets.QPushButton("Login")
        self.btn_login.setToolTip(
            "Set Username and API Key with entered values"
        )
        self.btn_login.clicked.connect(self._on_login_clicked)

        self.btn_ftrack_login = QtWidgets.QPushButton("Ftrack login")
        self.btn_ftrack_login.setToolTip("Open browser for Login to Ftrack")
        self.btn_ftrack_login.clicked.connect(self._on_ftrack_login_clicked)

        self.btn_logout = QtWidgets.QPushButton("Logout")
        self.btn_logout.clicked.connect(self._on_logout_clicked)

        self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_close.setToolTip("Close this window")
        self.btn_close.clicked.connect(self._close_widget)

        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addWidget(self.btn_advanced)
        btns_layout.addWidget(self.btn_simple)
        btns_layout.addStretch(1)
        btns_layout.addWidget(self.btn_ftrack_login)
        btns_layout.addWidget(self.btn_login)
        btns_layout.addWidget(self.btn_logout)
        btns_layout.addWidget(self.btn_close)

        self.note_label = QtWidgets.QLabel((
            "NOTE: Click on \"{}\" button to log with your default browser"
            " or click on \"{}\" button to enter API key manually."
        ).format(self.btn_ftrack_login.text(), self.btn_advanced.text()))

        self.note_label.setWordWrap(True)
        self.note_label.hide()

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        label_layout = QtWidgets.QVBoxLayout()
        label_layout.setContentsMargins(10, 5, 10, 5)
        label_layout.addWidget(self.note_label)
        label_layout.addWidget(self.error_label)

        main = QtWidgets.QVBoxLayout(self)
        main.addLayout(input_layout)
        main.addLayout(label_layout)
        main.addStretch(1)
        main.addLayout(btns_layout)

        self.fill_ftrack_url()

        self.set_is_logged(self._is_logged)

        self.setLayout(main)

    def fill_ftrack_url(self):
        url = os.getenv("FTRACK_SERVER")
        checked_url = self.check_url(url)

        if checked_url is None:
            checked_url = ""
            self.btn_login.setEnabled(False)
            self.btn_ftrack_login.setEnabled(False)

            self.api_input.setEnabled(False)
            self.user_input.setEnabled(False)
            self.ftsite_input.setEnabled(False)

        self.ftsite_input.setText(checked_url)

    def set_advanced_mode(self, is_advanced):
        self._in_advance_mode = is_advanced

        self.error_label.setVisible(False)

        is_logged = self._is_logged

        self.note_label.setVisible(not is_logged and not is_advanced)
        self.btn_ftrack_login.setVisible(not is_logged and not is_advanced)
        self.btn_advanced.setVisible(not is_logged and not is_advanced)

        self.btn_login.setVisible(not is_logged and is_advanced)
        self.btn_simple.setVisible(not is_logged and is_advanced)

        self.user_label.setVisible(is_logged or is_advanced)
        self.user_input.setVisible(is_logged or is_advanced)
        self.api_label.setVisible(is_logged or is_advanced)
        self.api_input.setVisible(is_logged or is_advanced)
        if is_advanced:
            self.user_input.setFocus()
        else:
            self.btn_ftrack_login.setFocus()

    def set_is_logged(self, is_logged):
        self._is_logged = is_logged

        self.user_input.setReadOnly(is_logged)
        self.api_input.setReadOnly(is_logged)
        self.user_input.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
        self.api_input.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))

        self.btn_logout.setVisible(is_logged)

        self.set_advanced_mode(self._in_advance_mode)

    def set_error(self, msg):
        self.error_label.setText(msg)
        self.error_label.show()

    def _on_logout_clicked(self):
        self.user_input.setText("")
        self.api_input.setText("")
        self.set_is_logged(False)
        self.logout_signal.emit()

    def _on_simple_clicked(self):
        self.set_advanced_mode(False)

    def _on_advanced_clicked(self):
        self.set_advanced_mode(True)

    def _user_changed(self):
        self._not_invalid_input(self.user_input)

    def _api_changed(self):
        self._not_invalid_input(self.api_input)

    def _not_invalid_input(self, input_widget):
        input_widget.setStyleSheet("")

    def _invalid_input(self, input_widget):
        input_widget.setStyleSheet("border: 1px solid red;")

    def _on_login(self):
        self.set_is_logged(True)
        self._close_widget()

    def _on_login_clicked(self):
        username = self.user_input.text().strip()
        api_key = self.api_input.text().strip()
        missing = []
        if username == "":
            missing.append("Username")
            self._invalid_input(self.user_input)

        if api_key == "":
            missing.append("API Key")
            self._invalid_input(self.api_input)

        if len(missing) > 0:
            self.set_error("You didn't enter {}".format(" and ".join(missing)))
            return

        if not self.login_with_credentials(username, api_key):
            self._invalid_input(self.user_input)
            self._invalid_input(self.api_input)
            self.set_error(
                "We're unable to sign in to Ftrack with these credentials"
            )

    def _on_ftrack_login_clicked(self):
        url = self.check_url(self.ftsite_input.text())
        if not url:
            return

        # If there is an existing server thread running we need to stop it.
        if self._login_server_thread:
            self._login_server_thread.join()
            self._login_server_thread = None

        # If credentials are not properly set, try to get them using a http
        # server.
        self._login_server_thread = login_tools.LoginServerThread(
            url, self._result_of_ftrack_thread
        )
        self._login_server_thread.start()

    def _result_of_ftrack_thread(self, username, api_key):
        if not self.login_with_credentials(username, api_key):
            self._invalid_input(self.api_input)
            self.set_error((
                "Somthing happened with Ftrack login."
                " Try enter Username and API key manually."
            ))

    def login_with_credentials(self, username, api_key):
        verification = credentials.check_credentials(username, api_key)
        if verification:
            credentials.save_credentials(username, api_key, False)
            credentials.set_env(username, api_key)
            self.set_credentials(username, api_key)
            self.login_changed.emit()
        return verification

    def set_credentials(self, username, api_key, is_logged=True):
        self.user_input.setText(username)
        self.api_input.setText(api_key)

        self.error_label.hide()

        self._not_invalid_input(self.ftsite_input)
        self._not_invalid_input(self.user_input)
        self._not_invalid_input(self.api_input)

        if is_logged is not None:
            self.set_is_logged(is_logged)

    def check_url(self, url):
        if url is not None:
            url = url.strip("/ ")

        if not url:
            self.set_error((
                "You need to specify a valid server URL, "
                "for example https://server-name.ftrackapp.com"
            ))
            return

        if "http" not in url:
            if url.endswith("ftrackapp.com"):
                url = "https://" + url
            else:
                url = "https://{}.ftrackapp.com".format(url)
        try:
            result = requests.get(
                url,
                # Old python API will not work with redirect.
                allow_redirects=False
            )
        except requests.exceptions.RequestException:
            self.set_error(
                "Specified URL could not be reached."
            )
            return

        if (
            result.status_code != 200
            or "FTRACK_VERSION" not in result.headers
        ):
            self.set_error(
                "Specified URL does not lead to a valid Ftrack server."
            )
            return
        return url

    def closeEvent(self, event):
        event.ignore()
        self._close_widget()

    def _close_widget(self):
        self.hide()
