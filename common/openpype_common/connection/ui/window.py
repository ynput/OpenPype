import traceback
from Qt import QtWidgets, QtCore, QtGui

from openpype_common.resources import (
    get_resource_path,
    get_icon_path,
    load_stylesheet,
)
from openpype_common.connection.server import (
    validate_url,
    UrlError,
    login,
)

from .widgets import (
    PressHoverButton,
    PlaceholderLineEdit,
)
from .lib import set_style_property


class ServerLoginWindow(QtWidgets.QDialog):
    default_width = 310
    default_height = 170

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        icon_path = get_icon_path()
        icon = QtGui.QIcon(icon_path)
        self.setWindowIcon(icon)
        self.setWindowTitle("Login to server")

        # --- URL page ---
        # TODO: add some details what is expected to fill
        url_widget = QtWidgets.QWidget(self)

        url_input = PlaceholderLineEdit(url_widget)
        url_input.setPlaceholderText("< https://openpype.server.com >")

        url_layout = QtWidgets.QFormLayout(url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.addRow("URL:", url_input)

        url_cred_sep = QtWidgets.QFrame(self)
        url_cred_sep.setObjectName("Separator")
        url_cred_sep.setMinimumHeight(2)
        url_cred_sep.setMaximumHeight(2)

        # --- Login page ---
        login_widget = QtWidgets.QWidget(self)

        user_cred_widget = QtWidgets.QWidget(login_widget)
        username_input = PlaceholderLineEdit(user_cred_widget)
        username_input.setPlaceholderText("< Artist >")

        password_widget = QtWidgets.QWidget(user_cred_widget)
        password_input = PlaceholderLineEdit(password_widget)
        password_input.setPlaceholderText("< *********** >")
        password_input.setEchoMode(password_input.Password)

        show_password_icon_path = get_resource_path("eye.png")
        show_password_icon = QtGui.QIcon(show_password_icon_path)
        show_password_btn = PressHoverButton(password_widget)
        show_password_btn.setObjectName("PasswordBtn")
        show_password_btn.setIcon(show_password_icon)
        show_password_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        password_layout = QtWidgets.QHBoxLayout(password_widget)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.addWidget(password_input, 1)
        password_layout.addWidget(show_password_btn, 0)

        # --- Credentials inputs ---
        user_cred_layout = QtWidgets.QFormLayout(user_cred_widget)
        user_cred_layout.setContentsMargins(0, 0, 0, 0)
        user_cred_layout.addRow("Username:", username_input)
        user_cred_layout.addRow("Password:", password_widget)

        login_layout = QtWidgets.QVBoxLayout(login_widget)
        login_layout.setContentsMargins(0, 0, 0, 0)
        login_layout.addWidget(user_cred_widget, 1)

        cred_msg_sep = QtWidgets.QFrame(self)
        cred_msg_sep.setObjectName("Separator")
        cred_msg_sep.setMinimumHeight(2)
        cred_msg_sep.setMaximumHeight(2)

        # --- Messages ---
        # Messages for users (e.g. invalid url etc.)
        message_label = QtWidgets.QLabel(self)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)

        footer_widget = QtWidgets.QWidget(self)
        login_btn = QtWidgets.QPushButton("Login", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(login_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(url_widget, 0)
        main_layout.addWidget(url_cred_sep, 0)
        main_layout.addWidget(login_widget, 0)
        main_layout.addWidget(cred_msg_sep, 0)
        main_layout.addWidget(message_label, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(footer_widget, 0)

        url_input.textChanged.connect(self._on_url_change)
        url_input.returnPressed.connect(self._on_url_enter_press)
        username_input.returnPressed.connect(self._on_username_enter_press)
        password_input.returnPressed.connect(self._on_password_enter_press)
        show_password_btn.change_state.connect(self._on_show_password)
        login_btn.clicked.connect(self._on_login_click)

        self._message_label = message_label

        self._url_widget = url_widget
        self._url_input = url_input

        self._login_widget = login_widget

        self._user_cred_widget = user_cred_widget
        self._username_input = username_input
        self._password_input = password_input

        self._login_btn = login_btn

        self._url_is_valid = None
        self._credentials_are_valid = None
        self._result = (None, None)
        self._first_show = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            self._on_first_show()

    def _on_first_show(self):
        self.setStyleSheet(load_stylesheet())
        self.resize(self.default_width, self.default_height)
        self._center_window()

        if self._url_input.text():
            widget = self._username_input
        else:
            widget = self._url_input

        self._set_input_focus(widget)

    def result(self):
        """Result url and token or login.

        Returns:
            Union[Tuple[str, str], Tuple[None, None]]: Url and token used for
                login if was successfull otherwise are both set to None.
        """
        return self._result

    def _center_window(self):
        """Move window to center of it's screen."""
        desktop = QtWidgets.QApplication.desktop()
        screen_idx = desktop.screenNumber(self)
        screen_geo = desktop.screenGeometry(screen_idx)
        geo = self.frameGeometry()
        geo.moveCenter(screen_geo.center())
        if geo.y() < screen_geo.y():
            geo.setY(screen_geo.y())

        self.move(geo.topLeft())

    def _on_url_change(self, text):
        if not text:
            self._login_btn.setEnabled(False)
        else:
            self._login_btn.setEnabled(True)
        self._set_url_valid(None)
        self._set_credentials_valid(None)

    def _set_url_valid(self, valid):
        if valid is self._url_is_valid:
            return

        self._url_is_valid = valid
        self._set_input_valid_state(self._url_input, valid)

    def _set_credentials_valid(self, valid):
        if self._credentials_are_valid is valid:
            return

        self._credentials_are_valid = valid
        self._set_input_valid_state(self._username_input, valid)
        self._set_input_valid_state(self._password_input, valid)

    def _on_url_enter_press(self):
        self._set_input_focus(self._username_input)

    def _on_username_enter_press(self):
        self._set_input_focus(self._password_input)

    def _on_password_enter_press(self):
        self._login()

    def _on_show_password(self, show_password):
        if show_password:
            placeholder_text = "< MySecret124 >"
            echo_mode = QtWidgets.QLineEdit.Normal
        else:
            placeholder_text = "< *********** >"
            echo_mode = QtWidgets.QLineEdit.Password

        self._password_input.setEchoMode(echo_mode)
        self._password_input.setPlaceholderText(placeholder_text)

    def _on_login_click(self):
        self._login()

    def _validate_url(self):
        """Use url from input, try connect and change window state on success.

        Todos:
            Threaded check.
        """

        url = self._url_input.text()
        valid_url = None
        try:
            valid_url = validate_url(url)

        except UrlError as exc:
            parts = ["<b>{}</b>".format(exc.title)]
            for hint in exc.hints:
                parts.append("- {}".format(hint))
            self._set_message("<br/>".join(parts))

        except KeyboardInterrupt:
            # Reraise KeyboardInterrupt error
            raise

        except BaseException:
            self._set_unexpected_error()
            return

        if valid_url is None:
            return False

        self._url_input.setText(valid_url)
        return True

    def _login(self):
        if not self._url_is_valid:
            self._set_url_valid(self._validate_url())

        if not self._url_is_valid:
            self._set_input_focus(self._url_input)
            self._set_credentials_valid(None)
            return

        self._clear_message()

        url = self._url_input.text()
        username = self._username_input.text()
        password = self._password_input.text()
        try:
            token = login(url, username, password)
        except BaseException:
            self._set_unexpected_error()
            return

        if token is not None:
            self._result = (url, token)
            self.accept()
            return

        self._set_credentials_valid(False)
        message_lines = ["<b>Invalid credentials</b>"]
        if not username.strip():
            message_lines.append("- Username is not filled")

        if not password.strip():
            message_lines.append("- Password is not filled")

        if username and password:
            message_lines.append("- Check your credentials")

        self._set_message("<br/>".join(message_lines))
        self._set_input_focus(self._username_input)

    def _set_input_focus(self, widget):
        widget.setFocus(QtCore.Qt.MouseFocusReason)

    def _set_input_valid_state(self, widget, valid):
        state = ""
        if valid:
            state = "valid"
        elif not valid:
            state = "invalid"
        set_style_property(widget, "state", state)

    def _set_message(self, message):
        self._message_label.setText(message)

    def _clear_message(self):
        self._message_label.setText("")

    def _set_unexpected_error(self):
        # TODO add traceback somewhere
        # - maybe a button to show or copy?
        traceback.print_exc()
        lines = [
            "<b>Unexpected error happened</b>",
            "- Can be caused by wrong url (leading elsewhere)"
        ]
        self._set_message("<br/>".join(lines))

    def set_url(self, url):
        self._url_input.setText(url)
        self._validate_url()


def ask_to_login(url=None):
    """Ask user to login using Qt dialog.

    Function creates new QApplication if is not created yet.

    Args:
        url (str): Server url that will be prefilled in dialog.

    Returns:
        Tuple[str, str]: Returns Url and user's token. Url can be changed
            during dialog lifetime that's why the url is returned.
    """

    app_instance = QtWidgets.QApplication.instance()
    if app_instance is None:
        for attr_name in (
            "AA_EnableHighDpiScaling",
            "AA_UseHighDpiPixmaps"
        ):
            attr = getattr(QtCore.Qt, attr_name, None)
            if attr is not None:
                QtWidgets.QApplication.setAttribute(attr)
        app_instance = QtWidgets.QApplication([])

    window = ServerLoginWindow()
    if url:
        window.set_url(url)

    def _exec_window():
        window.exec_()
        return window.result()

    # Use QTimer to exec dialog if application is not running yet
    # - it is not possible to call 'exec_' on dialog without running app
    #   - it is but the window is stuck
    if app_instance.startingUp():
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(_exec_window)
        timer.start()
        # This can became main Qt loop. Maybe should live elsewhere
        app_instance.exec_()
    return _exec_window()
