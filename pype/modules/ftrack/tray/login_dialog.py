import os
import requests
from avalon import style
from pype.modules.ftrack import credentials
from . import login_tools
from Qt import QtCore, QtGui, QtWidgets


class Login_Dialog_ui(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 230

    loginSignal = QtCore.Signal(object, object, object)
    _login_server_thread = None
    inputs = []
    buttons = []
    labels = []

    def __init__(self, parent=None, is_event=False):

        super(Login_Dialog_ui, self).__init__()

        self.parent = parent
        self.is_event = is_event

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

        self.loginSignal.connect(self.loginWithCredentials)
        self._translate = QtCore.QCoreApplication.translate

        self.font = QtGui.QFont()
        self.font.setFamily("DejaVu Sans Condensed")
        self.font.setPointSize(9)
        self.font.setBold(True)
        self.font.setWeight(50)
        self.font.setKerning(True)

        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W+100, self.SIZE_H+100))
        self.setStyleSheet(style.load_stylesheet())

        self.setLayout(self._main())
        self.setWindowTitle('Pype - Ftrack Login')

    def _main(self):
        self.main = QtWidgets.QVBoxLayout()
        self.main.setObjectName("main")

        self.form = QtWidgets.QFormLayout()
        self.form.setContentsMargins(10, 15, 10, 5)
        self.form.setObjectName("form")

        self.ftsite_label = QtWidgets.QLabel("FTrack URL:")
        self.ftsite_label.setFont(self.font)
        self.ftsite_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.ftsite_label.setTextFormat(QtCore.Qt.RichText)
        self.ftsite_label.setObjectName("user_label")

        self.ftsite_input = QtWidgets.QLineEdit()
        self.ftsite_input.setEnabled(True)
        self.ftsite_input.setFrame(True)
        self.ftsite_input.setEnabled(False)
        self.ftsite_input.setReadOnly(True)
        self.ftsite_input.setObjectName("ftsite_input")

        self.user_label = QtWidgets.QLabel("Username:")
        self.user_label.setFont(self.font)
        self.user_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.user_label.setTextFormat(QtCore.Qt.RichText)
        self.user_label.setObjectName("user_label")

        self.user_input = QtWidgets.QLineEdit()
        self.user_input.setEnabled(True)
        self.user_input.setFrame(True)
        self.user_input.setObjectName("user_input")
        self.user_input.setPlaceholderText(
            self._translate("main", "user.name")
        )
        self.user_input.textChanged.connect(self._user_changed)

        self.api_label = QtWidgets.QLabel("API Key:")
        self.api_label.setFont(self.font)
        self.api_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.api_label.setTextFormat(QtCore.Qt.RichText)
        self.api_label.setObjectName("api_label")

        self.api_input = QtWidgets.QLineEdit()
        self.api_input.setEnabled(True)
        self.api_input.setFrame(True)
        self.api_input.setObjectName("api_input")
        self.api_input.setPlaceholderText(self._translate(
            "main", "e.g. xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        ))
        self.api_input.textChanged.connect(self._api_changed)

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setFont(self.font)
        self.error_label.setTextFormat(QtCore.Qt.RichText)
        self.error_label.setObjectName("error_label")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.form.addRow(self.ftsite_label, self.ftsite_input)
        self.form.addRow(self.user_label, self.user_input)
        self.form.addRow(self.api_label, self.api_input)
        self.form.addRow(self.error_label)

        self.btnGroup = QtWidgets.QHBoxLayout()
        self.btnGroup.addStretch(1)
        self.btnGroup.setObjectName("btnGroup")

        self.btnEnter = QtWidgets.QPushButton("Login")
        self.btnEnter.setToolTip(
            'Set Username and API Key with entered values'
        )
        self.btnEnter.clicked.connect(self.enter_credentials)

        self.btnClose = QtWidgets.QPushButton("Close")
        self.btnClose.setToolTip('Close this window')
        self.btnClose.clicked.connect(self._close_widget)

        self.btnFtrack = QtWidgets.QPushButton("Ftrack")
        self.btnFtrack.setToolTip('Open browser for Login to Ftrack')
        self.btnFtrack.clicked.connect(self.open_ftrack)

        self.btnGroup.addWidget(self.btnFtrack)
        self.btnGroup.addWidget(self.btnEnter)
        self.btnGroup.addWidget(self.btnClose)

        self.main.addLayout(self.form)
        self.main.addLayout(self.btnGroup)

        self.inputs.append(self.api_input)
        self.inputs.append(self.user_input)
        self.inputs.append(self.ftsite_input)

        self.enter_site()
        return self.main

    def enter_site(self):
        try:
            url = os.getenv('FTRACK_SERVER')
            newurl = self.checkUrl(url)

            if newurl is None:
                self.btnEnter.setEnabled(False)
                self.btnFtrack.setEnabled(False)
                for input in self.inputs:
                    input.setEnabled(False)
                newurl = url

            self.ftsite_input.setText(newurl)

        except Exception:
            self.setError("FTRACK_SERVER is not set in templates")
            self.btnEnter.setEnabled(False)
            self.btnFtrack.setEnabled(False)
            for input in self.inputs:
                input.setEnabled(False)

    def setError(self, msg):
        self.error_label.setText(msg)
        self.error_label.show()

    def _user_changed(self):
        self.user_input.setStyleSheet("")

    def _api_changed(self):
        self.api_input.setStyleSheet("")

    def _invalid_input(self, entity):
        entity.setStyleSheet("border: 1px solid red;")

    def enter_credentials(self):
        username = self.user_input.text().strip()
        apiKey = self.api_input.text().strip()
        msg = "You didn't enter "
        missing = []
        if username == "":
            missing.append("Username")
            self._invalid_input(self.user_input)

        if apiKey == "":
            missing.append("API Key")
            self._invalid_input(self.api_input)

        if len(missing) > 0:
            self.setError("{0} {1}".format(msg, " and ".join(missing)))
            return

        verification = credentials.check_credentials(username, apiKey)

        if verification:
            credentials.save_credentials(username, apiKey, self.is_event)
            credentials.set_env(username, apiKey)
            if self.parent is not None:
                self.parent.loginChange()
            self._close_widget()
        else:
            self._invalid_input(self.user_input)
            self._invalid_input(self.api_input)
            self.setError(
                "We're unable to sign in to Ftrack with these credentials"
            )

    def open_ftrack(self):
        url = self.ftsite_input.text()
        self.loginWithCredentials(url, None, None)

    def checkUrl(self, url):
        url = url.strip('/ ')

        if not url:
            self.setError("There is no URL set in Templates")
            return

        if 'http' not in url:
            if url.endswith('ftrackapp.com'):
                url = 'https://' + url
            else:
                url = 'https://{0}.ftrackapp.com'.format(url)
        try:
            result = requests.get(
                url,
                # Old python API will not work with redirect.
                allow_redirects=False
            )
        except requests.exceptions.RequestException:
            self.setError(
                'The server URL set in Templates could not be reached.'
            )
            return

        if (
            result.status_code != 200 or 'FTRACK_VERSION' not in result.headers
        ):
            self.setError(
                'The server URL set in Templates is not a valid ftrack server.'
            )
            return
        return url

    def loginWithCredentials(self, url, username, apiKey):
        url = url.strip('/ ')

        if not url:
            self.setError(
                'You need to specify a valid server URL, '
                'for example https://server-name.ftrackapp.com'
            )
            return

        if 'http' not in url:
            if url.endswith('ftrackapp.com'):
                url = 'https://' + url
            else:
                url = 'https://{0}.ftrackapp.com'.format(url)
        try:
            result = requests.get(
                url,
                # Old python API will not work with redirect.
                allow_redirects=False
            )
        except requests.exceptions.RequestException:
            self.setError(
                'The server URL you provided could not be reached.'
            )
            return

        if (
            result.status_code != 200 or 'FTRACK_VERSION' not in result.headers
        ):
            self.setError(
                'The server URL you provided is not a valid ftrack server.'
            )
            return

        # If there is an existing server thread running we need to stop it.
        if self._login_server_thread:
            self._login_server_thread.quit()
            self._login_server_thread = None

        # If credentials are not properly set, try to get them using a http
        # server.
        if not username or not apiKey:
            self._login_server_thread = login_tools.LoginServerThread()
            self._login_server_thread.loginSignal.connect(self.loginSignal)
            self._login_server_thread.start(url)
            return

        verification = credentials.check_credentials(username, apiKey)

        if verification is True:
            credentials.save_credentials(username, apiKey, self.is_event)
            credentials.set_env(username, apiKey)
            if self.parent is not None:
                self.parent.loginChange()
            self._close_widget()

    def closeEvent(self, event):
        event.ignore()
        self._close_widget()

    def _close_widget(self):
        self.hide()
