import traceback

from qtpy import QtWidgets, QtCore, QtGui

from ayon_api.exceptions import UrlError
from ayon_api.utils import validate_url, login_to_server

from ayon_common.resources import (
    get_resource_path,
    get_icon_path,
    load_stylesheet,
)
from ayon_common.ui_utils import set_style_property, get_qt_app

from .widgets import (
    PressHoverButton,
    PlaceholderLineEdit,
)


class LogoutConfirmDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Logout confirmation")

        message_widget = QtWidgets.QWidget(self)

        message_label = QtWidgets.QLabel(
            (
                "You are going to logout. This action will close this"
                " application and will invalidate your login."
                " All other applications launched with this login won't be"
                " able to use it anymore.<br/><br/>"
                "You can cancel logout and only change server and user login"
                " in login dialog.<br/><br/>"
                "Press OK to confirm logout."
            ),
            message_widget
        )
        message_label.setWordWrap(True)

        message_layout = QtWidgets.QHBoxLayout(message_widget)
        message_layout.setContentsMargins(0, 0, 0, 0)
        message_layout.addWidget(message_label, 1)

        sep_frame = QtWidgets.QFrame(self)
        sep_frame.setObjectName("Separator")
        sep_frame.setMinimumHeight(2)
        sep_frame.setMaximumHeight(2)

        footer_widget = QtWidgets.QWidget(self)

        cancel_btn = QtWidgets.QPushButton("Cancel", footer_widget)
        confirm_btn = QtWidgets.QPushButton("OK", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(cancel_btn, 0)
        footer_layout.addWidget(confirm_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(message_widget, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(sep_frame, 0)
        main_layout.addWidget(footer_widget, 0)

        cancel_btn.clicked.connect(self._on_cancel_click)
        confirm_btn.clicked.connect(self._on_confirm_click)

        self._cancel_btn = cancel_btn
        self._confirm_btn = confirm_btn
        self._result = False

    def showEvent(self, event):
        super().showEvent(event)
        self._match_btns_sizes()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._match_btns_sizes()

    def _match_btns_sizes(self):
        width = max(
            self._cancel_btn.sizeHint().width(),
            self._confirm_btn.sizeHint().width()
        )
        self._cancel_btn.setMinimumWidth(width)
        self._confirm_btn.setMinimumWidth(width)

    def _on_cancel_click(self):
        self._result = False
        self.reject()

    def _on_confirm_click(self):
        self._result = True
        self.accept()

    def get_result(self):
        return self._result


class ServerLoginWindow(QtWidgets.QDialog):
    default_width = 410
    default_height = 170

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        icon_path = get_icon_path()
        icon = QtGui.QIcon(icon_path)
        self.setWindowIcon(icon)
        self.setWindowTitle("Login to server")

        edit_icon_path = get_resource_path("edit.png")
        edit_icon = QtGui.QIcon(edit_icon_path)

        # --- URL page ---
        login_widget = QtWidgets.QWidget(self)

        user_cred_widget = QtWidgets.QWidget(login_widget)

        url_label = QtWidgets.QLabel("URL:", user_cred_widget)

        url_widget = QtWidgets.QWidget(user_cred_widget)

        url_input = PlaceholderLineEdit(url_widget)
        url_input.setPlaceholderText("< https://ayon.server.com >")

        url_preview = QtWidgets.QLineEdit(url_widget)
        url_preview.setReadOnly(True)
        url_preview.setObjectName("LikeDisabledInput")

        url_edit_btn = PressHoverButton(user_cred_widget)
        url_edit_btn.setIcon(edit_icon)
        url_edit_btn.setObjectName("PasswordBtn")

        url_layout = QtWidgets.QHBoxLayout(url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.addWidget(url_input, 1)
        url_layout.addWidget(url_preview, 1)

        # --- URL separator ---
        url_cred_sep = QtWidgets.QFrame(self)
        url_cred_sep.setObjectName("Separator")
        url_cred_sep.setMinimumHeight(2)
        url_cred_sep.setMaximumHeight(2)

        # --- Login page ---
        username_label = QtWidgets.QLabel("Username:", user_cred_widget)

        username_widget = QtWidgets.QWidget(user_cred_widget)

        username_input = PlaceholderLineEdit(username_widget)
        username_input.setPlaceholderText("< Artist >")

        username_preview = QtWidgets.QLineEdit(username_widget)
        username_preview.setReadOnly(True)
        username_preview.setObjectName("LikeDisabledInput")

        username_edit_btn = PressHoverButton(user_cred_widget)
        username_edit_btn.setIcon(edit_icon)
        username_edit_btn.setObjectName("PasswordBtn")

        username_layout = QtWidgets.QHBoxLayout(username_widget)
        username_layout.setContentsMargins(0, 0, 0, 0)
        username_layout.addWidget(username_input, 1)
        username_layout.addWidget(username_preview, 1)

        password_label = QtWidgets.QLabel("Password:", user_cred_widget)
        password_input = PlaceholderLineEdit(user_cred_widget)
        password_input.setPlaceholderText("< *********** >")
        password_input.setEchoMode(PlaceholderLineEdit.Password)

        api_label = QtWidgets.QLabel("API key:", user_cred_widget)
        api_preview = QtWidgets.QLineEdit(user_cred_widget)
        api_preview.setReadOnly(True)
        api_preview.setObjectName("LikeDisabledInput")

        show_password_icon_path = get_resource_path("eye.png")
        show_password_icon = QtGui.QIcon(show_password_icon_path)
        show_password_btn = PressHoverButton(user_cred_widget)
        show_password_btn.setObjectName("PasswordBtn")
        show_password_btn.setIcon(show_password_icon)
        show_password_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        cred_msg_sep = QtWidgets.QFrame(self)
        cred_msg_sep.setObjectName("Separator")
        cred_msg_sep.setMinimumHeight(2)
        cred_msg_sep.setMaximumHeight(2)

        # --- Credentials inputs ---
        user_cred_layout = QtWidgets.QGridLayout(user_cred_widget)
        user_cred_layout.setContentsMargins(0, 0, 0, 0)
        row = 0

        user_cred_layout.addWidget(url_label, row, 0, 1, 1)
        user_cred_layout.addWidget(url_widget, row, 1, 1, 1)
        user_cred_layout.addWidget(url_edit_btn, row, 2, 1, 1)
        row += 1

        user_cred_layout.addWidget(url_cred_sep, row, 0, 1, 3)
        row += 1

        user_cred_layout.addWidget(username_label, row, 0, 1, 1)
        user_cred_layout.addWidget(username_widget, row, 1, 1, 1)
        user_cred_layout.addWidget(username_edit_btn, row, 2, 2, 1)
        row += 1

        user_cred_layout.addWidget(api_label, row, 0, 1, 1)
        user_cred_layout.addWidget(api_preview, row, 1, 1, 1)
        row += 1

        user_cred_layout.addWidget(password_label, row, 0, 1, 1)
        user_cred_layout.addWidget(password_input, row, 1, 1, 1)
        user_cred_layout.addWidget(show_password_btn, row, 2, 1, 1)
        row += 1

        user_cred_layout.addWidget(cred_msg_sep, row, 0, 1, 3)
        row += 1

        user_cred_layout.setColumnStretch(0, 0)
        user_cred_layout.setColumnStretch(1, 1)
        user_cred_layout.setColumnStretch(2, 0)

        login_layout = QtWidgets.QVBoxLayout(login_widget)
        login_layout.setContentsMargins(0, 0, 0, 0)
        login_layout.addWidget(user_cred_widget, 1)

        # --- Messages ---
        # Messages for users (e.g. invalid url etc.)
        message_label = QtWidgets.QLabel(self)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)

        footer_widget = QtWidgets.QWidget(self)
        logout_btn = QtWidgets.QPushButton("Logout", footer_widget)
        user_message = QtWidgets.QLabel(footer_widget)
        login_btn = QtWidgets.QPushButton("Login", footer_widget)
        confirm_btn = QtWidgets.QPushButton("Confirm", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(logout_btn, 0)
        footer_layout.addWidget(user_message, 1)
        footer_layout.addWidget(login_btn, 0)
        footer_layout.addWidget(confirm_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(login_widget, 0)
        main_layout.addWidget(message_label, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(footer_widget, 0)

        url_input.textChanged.connect(self._on_url_change)
        url_input.returnPressed.connect(self._on_url_enter_press)
        username_input.textChanged.connect(self._on_user_change)
        username_input.returnPressed.connect(self._on_username_enter_press)
        password_input.returnPressed.connect(self._on_password_enter_press)
        show_password_btn.change_state.connect(self._on_show_password)
        url_edit_btn.clicked.connect(self._on_url_edit_click)
        username_edit_btn.clicked.connect(self._on_username_edit_click)
        logout_btn.clicked.connect(self._on_logout_click)
        login_btn.clicked.connect(self._on_login_click)
        confirm_btn.clicked.connect(self._on_login_click)

        self._message_label = message_label

        self._url_widget = url_widget
        self._url_input = url_input
        self._url_preview = url_preview
        self._url_edit_btn = url_edit_btn

        self._login_widget = login_widget

        self._user_cred_widget = user_cred_widget
        self._username_input = username_input
        self._username_preview = username_preview
        self._username_edit_btn = username_edit_btn

        self._password_label = password_label
        self._password_input = password_input
        self._show_password_btn = show_password_btn
        self._api_label = api_label
        self._api_preview = api_preview

        self._logout_btn = logout_btn
        self._user_message = user_message
        self._login_btn = login_btn
        self._confirm_btn = confirm_btn

        self._url_is_valid = None
        self._credentials_are_valid = None
        self._result = (None, None, None, False)
        self._first_show = True

        self._allow_logout = False
        self._logged_in = False
        self._url_edit_mode = False
        self._username_edit_mode = False

    def set_allow_logout(self, allow_logout):
        if allow_logout is self._allow_logout:
            return
        self._allow_logout = allow_logout

        self._update_states_by_edit_mode()

    def _set_logged_in(self, logged_in):
        if logged_in is self._logged_in:
            return
        self._logged_in = logged_in

        self._update_states_by_edit_mode()

    def _set_url_edit_mode(self, edit_mode):
        if self._url_edit_mode is not edit_mode:
            self._url_edit_mode = edit_mode
            self._update_states_by_edit_mode()

    def _set_username_edit_mode(self, edit_mode):
        if self._username_edit_mode is not edit_mode:
            self._username_edit_mode = edit_mode
            self._update_states_by_edit_mode()

    def _get_url_user_edit(self):
        url_edit = True
        if self._logged_in and not self._url_edit_mode:
            url_edit = False
        user_edit = url_edit
        if not user_edit and self._logged_in and self._username_edit_mode:
            user_edit = True
        return url_edit, user_edit

    def _update_states_by_edit_mode(self):
        url_edit, user_edit = self._get_url_user_edit()

        self._url_preview.setVisible(not url_edit)
        self._url_input.setVisible(url_edit)
        self._url_edit_btn.setVisible(self._allow_logout and not url_edit)

        self._username_preview.setVisible(not user_edit)
        self._username_input.setVisible(user_edit)
        self._username_edit_btn.setVisible(
            self._allow_logout and not user_edit
        )

        self._api_preview.setVisible(not user_edit)
        self._api_label.setVisible(not user_edit)

        self._password_label.setVisible(user_edit)
        self._show_password_btn.setVisible(user_edit)
        self._password_input.setVisible(user_edit)

        self._logout_btn.setVisible(self._allow_logout and self._logged_in)
        self._login_btn.setVisible(not self._allow_logout)
        self._confirm_btn.setVisible(self._allow_logout)
        self._update_login_btn_state(url_edit, user_edit)

    def _update_login_btn_state(self, url_edit=None, user_edit=None, url=None):
        if url_edit is None:
            url_edit, user_edit = self._get_url_user_edit()

        if url is None:
            url = self._url_input.text()

        enabled = bool(url) and (url_edit or user_edit)

        self._login_btn.setEnabled(enabled)
        self._confirm_btn.setEnabled(enabled)

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            self._on_first_show()

    def _on_first_show(self):
        self.setStyleSheet(load_stylesheet())
        self.resize(self.default_width, self.default_height)
        self._center_window()
        if self._allow_logout is None:
            self.set_allow_logout(False)

        self._update_states_by_edit_mode()
        if not self._url_input.text():
            widget = self._url_input
        elif not self._username_input.text():
            widget = self._username_input
        else:
            widget = self._password_input

        self._set_input_focus(widget)

    def result(self):
        """Result url and token or login.

        Returns:
            Union[Tuple[str, str], Tuple[None, None]]: Url and token used for
                login if was successful otherwise are both set to None.
        """
        return self._result

    def _center_window(self):
        """Move window to center of screen."""

        if hasattr(QtWidgets.QApplication, "desktop"):
            desktop = QtWidgets.QApplication.desktop()
            screen_idx = desktop.screenNumber(self)
            screen_geo = desktop.screenGeometry(screen_idx)
        else:
            screen = self.screen()
            screen_geo = screen.geometry()

        geo = self.frameGeometry()
        geo.moveCenter(screen_geo.center())
        if geo.y() < screen_geo.y():
            geo.setY(screen_geo.y())
        self.move(geo.topLeft())

    def _on_url_change(self, text):
        self._update_login_btn_state(url=text)
        self._set_url_valid(None)
        self._set_credentials_valid(None)
        self._url_preview.setText(text)

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

    def _on_user_change(self, username):
        self._username_preview.setText(username)

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

    def _on_username_edit_click(self):
        self._username_edit_mode = True
        self._update_states_by_edit_mode()

    def _on_url_edit_click(self):
        self._url_edit_mode = True
        self._update_states_by_edit_mode()

    def _on_logout_click(self):
        dialog = LogoutConfirmDialog(self)
        dialog.exec_()
        if dialog.get_result():
            self._result = (None, None, None, True)
            self.accept()

    def _on_login_click(self):
        self._login()

    def _validate_url(self):
        """Use url from input to connect and change window state on success.

        Todos:
            Threaded check.
        """

        url = self._url_input.text()
        valid_url = None
        try:
            valid_url = validate_url(url)

        except UrlError as exc:
            parts = [f"<b>{exc.title}</b>"]
            parts.extend(f"- {hint}" for hint in exc.hints)
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
        if (
            not self._login_btn.isEnabled()
            and not self._confirm_btn.isEnabled()
        ):
            return

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
            token = login_to_server(url, username, password)
        except BaseException:
            self._set_unexpected_error()
            return

        if token is not None:
            self._result = (url, token, username, False)
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
        if valid is True:
            state = "valid"
        elif valid is False:
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
        self._url_preview.setText(url)
        self._url_input.setText(url)
        self._validate_url()

    def set_username(self, username):
        self._username_preview.setText(username)
        self._username_input.setText(username)

    def _set_api_key(self, api_key):
        if not api_key or len(api_key) < 3:
            self._api_preview.setText(api_key or "")
            return

        api_key_len = len(api_key)
        offset = 6
        if api_key_len < offset:
            offset = api_key_len // 2
        api_key = api_key[:offset] + "." * (api_key_len - offset)

        self._api_preview.setText(api_key)

    def set_logged_in(
        self,
        logged_in,
        url=None,
        username=None,
        api_key=None,
        allow_logout=None
    ):
        if url is not None:
            self.set_url(url)

        if username is not None:
            self.set_username(username)

        if api_key:
            self._set_api_key(api_key)

        if logged_in and allow_logout is None:
            allow_logout = True

        self._set_logged_in(logged_in)

        if allow_logout:
            self.set_allow_logout(True)
        elif allow_logout is False:
            self.set_allow_logout(False)


def ask_to_login(url=None, username=None, always_on_top=False):
    """Ask user to login using Qt dialog.

    Function creates new QApplication if is not created yet.

    Args:
        url (Optional[str]): Server url that will be prefilled in dialog.
        username (Optional[str]): Username that will be prefilled in dialog.
        always_on_top (Optional[bool]): Window will be drawn on top of
            other windows.

    Returns:
        tuple[str, str, str]: Returns Url, user's token and username. Url can
            be changed during dialog lifetime that's why the url is returned.
    """

    app_instance = get_qt_app()

    window = ServerLoginWindow()
    if always_on_top:
        window.setWindowFlags(
            window.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )

    if url:
        window.set_url(url)

    if username:
        window.set_username(username)

    if not app_instance.startingUp():
        window.exec_()
    else:
        window.open()
        app_instance.exec_()
    result = window.result()
    out_url, out_token, out_username, _ = result
    return out_url, out_token, out_username


def change_user(url, username, api_key, always_on_top=False):
    """Ask user to login using Qt dialog.

    Function creates new QApplication if is not created yet.

    Args:
        url (str): Server url that will be prefilled in dialog.
        username (str): Username that will be prefilled in dialog.
        api_key (str): API key that will be prefilled in dialog.
        always_on_top (Optional[bool]): Window will be drawn on top of
            other windows.

    Returns:
        Tuple[str, str]: Returns Url and user's token. Url can be changed
            during dialog lifetime that's why the url is returned.
    """

    app_instance = get_qt_app()
    window = ServerLoginWindow()
    if always_on_top:
        window.setWindowFlags(
            window.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )
    window.set_logged_in(True, url, username, api_key)

    if not app_instance.startingUp():
        window.exec_()
    else:
        window.open()
        # This can become main Qt loop. Maybe should live elsewhere
        app_instance.exec_()
    return window.result()
