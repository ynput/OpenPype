import os
from Qt import QtCore, QtWidgets, QtGui

from openpype import style
from openpype import resources
from openpype.modules.shotgrid.lib import settings, credentials


class CredentialsDialog(QtWidgets.QDialog):
    SIZE_W = 450
    SIZE_H = 200

    _module = None
    _is_logged = False
    url_label = None
    login_label = None
    password_label = None
    url_input = None
    login_input = None
    password_input = None
    input_layout = None
    login_button = None
    buttons_layout = None
    main_widget = None

    login_changed = QtCore.Signal()

    def __init__(self, module, parent=None):
        super(CredentialsDialog, self).__init__(parent)

        self._module = module
        self._is_logged = False

        self.setWindowTitle("OpenPype - Shotgrid Login")

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W + 100, self.SIZE_H + 100))
        self.setStyleSheet(style.load_stylesheet())

        self.ui_init()

    def ui_init(self):
        self.url_label = QtWidgets.QLabel("Shotgrid server:")
        self.login_label = QtWidgets.QLabel("Login:")
        self.password_label = QtWidgets.QLabel("Password:")

        self.url_input = QtWidgets.QComboBox()
        # self.url_input.setReadOnly(True)

        self.login_input = QtWidgets.QLineEdit()
        self.login_input.setPlaceholderText("login")

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.input_layout = QtWidgets.QFormLayout()
        self.input_layout.setContentsMargins(10, 15, 10, 5)

        self.input_layout.addRow(self.url_label, self.url_input)
        self.input_layout.addRow(self.login_label, self.login_input)
        self.input_layout.addRow(self.password_label, self.password_input)
        self.input_layout.addRow(self.error_label)

        self.login_button = QtWidgets.QPushButton("Login")
        self.login_button.setToolTip("Log in shotgrid instance")
        self.login_button.clicked.connect(self._on_shotgrid_login_clicked)

        self.logout_button = QtWidgets.QPushButton("Logout")
        self.logout_button.setToolTip("Log out shotgrid instance")
        self.logout_button.clicked.connect(self._on_shotgrid_logout_clicked)

        self.buttons_layout = QtWidgets.QHBoxLayout()
        self.buttons_layout.addWidget(self.logout_button)
        self.buttons_layout.addWidget(self.login_button)

        self.main_widget = QtWidgets.QVBoxLayout(self)
        self.main_widget.addLayout(self.input_layout)
        self.main_widget.addLayout(self.buttons_layout)
        self.setLayout(self.main_widget)

    def show(self, *args, **kwargs):
        super(CredentialsDialog, self).show(*args, **kwargs)
        self._fill_shotgrid_url()
        self._fill_shotgrid_login()

    def _fill_shotgrid_url(self):
        servers = settings.get_shotgrid_servers()

        if servers:
            for _, v in servers.items():
                self.url_input.addItem("{}".format(v.get('shotgrid_url')))
            self._valid_input(self.url_input)
            self.login_button.show()
            self.logout_button.show()
            enabled = True
        else:
            self.set_error("Ask your admin to add shotgrid server in settings")
            self._invalid_input(self.url_input)
            self.login_button.hide()
            self.logout_button.hide()
            enabled = False

        self.login_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)

    def _fill_shotgrid_login(self):
        login = credentials.get_local_login()

        if login:
            self.login_input.setText(login)

    def _clear_shotgrid_login(self):
        self.login_input.setText("")
        self.password_input.setText("")

    def _on_shotgrid_login_clicked(self):
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()
        missing = []

        if login == "":
            missing.append("login")
            self._invalid_input(self.login_input)

        if password == "":
            missing.append("password")
            self._invalid_input(self.password_input)

        url = self.url_input.currentText()
        if url == "":
            missing.append("url")
            self._invalid_input(self.url_input)

        if len(missing) > 0:
            self.set_error("You didn't enter {}".format(" and ".join(missing)))
            return

        # if credentials.check_credentials(
        #     login=login,
        #     password=password,
        #     shotgrid_url=url,
        # ):
        credentials.save_local_login(
            login=login
        )
        os.environ['OPENPYPE_SG_USER'] = login
        self._on_login()

        self.set_error("CANT LOGIN")

    def _on_shotgrid_logout_clicked(self):
        credentials.clear_local_login()
        del os.environ['OPENPYPE_SG_USER']
        self._clear_shotgrid_login()
        self._on_logout()

    def set_error(self, msg):
        self.error_label.setText(msg)
        self.error_label.show()

    def _on_login(self):
        self._is_logged = True
        self.login_changed.emit()
        self._close_widget()

    def _on_logout(self):
        self._is_logged = False
        self.login_changed.emit()

    def _close_widget(self):
        self.hide()

    def _valid_input(self, input_widget):
        input_widget.setStyleSheet("")

    def _invalid_input(self, input_widget):
        input_widget.setStyleSheet("border: 1px solid red;")

    def login_with_credentials(
        self, url, login, password
    ):
        verification = credentials.check_credentials(url, login, password)
        if verification:
            credentials.save_credentials(login, password, False)
            self._module.set_credentials_to_env(login, password)
            self.set_credentials(login, password)
            self.login_changed.emit()
        return verification
