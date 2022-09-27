from Qt import QtWidgets, QtCore, QtGui
from openpype_common.connection import validate_url, UrlError, login
from openpype_common.resources import get_icon_path, load_stylesheet


class ServerLoginWindow(QtWidgets.QDialog):
    default_width = 310
    default_height = 170

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        icon_path = get_icon_path()
        icon = QtGui.QIcon(icon_path)
        self.setWindowIcon(icon)
        self.setWindowTitle("Login to server")

        # Content - whare are inputs
        content_widget = QtWidgets.QWidget(self)
        # Message - messages for users (e.g. invalid url etc.)
        message_label = QtWidgets.QLabel(self)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)

        # --- URL page ---
        # TODO: add some details what is expected to fill
        url_widget = QtWidgets.QWidget(content_widget)

        url_input = QtWidgets.QLineEdit(url_widget)

        url_layout = QtWidgets.QFormLayout(url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.addRow("URL:", url_input)

        # --- Login page ---
        login_widget = QtWidgets.QWidget(content_widget)

        user_cred_widget = QtWidgets.QWidget(login_widget)
        username_input = QtWidgets.QLineEdit(user_cred_widget)
        password_input = QtWidgets.QLineEdit(user_cred_widget)
        password_input.setEchoMode(password_input.Password)

        # --- Credentials inputs ---
        user_cred_layout = QtWidgets.QFormLayout(user_cred_widget)
        user_cred_layout.setContentsMargins(0, 0, 0, 0)
        user_cred_layout.addRow("Username:", username_input)
        user_cred_layout.addRow("Password:", password_input)

        login_layout = QtWidgets.QVBoxLayout(login_widget)
        login_layout.setContentsMargins(0, 0, 0, 0)
        login_layout.addWidget(user_cred_widget, 1)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(url_widget, 0)
        content_layout.addWidget(login_widget, 0)
        content_layout.addStretch(1)

        footer_widget = QtWidgets.QWidget(self)
        connect_btn = QtWidgets.QPushButton("Connect", footer_widget)
        change_server_btn = QtWidgets.QPushButton("Change URL", footer_widget)
        login_btn = QtWidgets.QPushButton("Login", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(change_server_btn, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(connect_btn, 0)
        footer_layout.addWidget(login_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(content_widget, 0)
        main_layout.addWidget(message_label, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(footer_widget, 0)

        url_input.textChanged.connect(self._on_url_change)
        url_input.returnPressed.connect(self._on_url_enter_press)
        connect_btn.clicked.connect(self._on_connect_click)
        username_input.returnPressed.connect(self._on_username_enter_press)
        password_input.returnPressed.connect(self._on_password_enter_press)
        change_server_btn.clicked.connect(self._on_change_server_click)
        login_btn.clicked.connect(self._on_login_click)

        self._message_label = message_label

        self._url_widget = url_widget
        self._url_input = url_input
        self._connect_btn = connect_btn

        self._login_widget = login_widget

        self._user_cred_widget = user_cred_widget
        self._username_input = username_input
        self._password_input = password_input

        self._change_server_btn = change_server_btn
        self._login_btn = login_btn

        self._result = (None, None)
        self._first_show = True
        self._page = 0
        self._update_visibilities()

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(load_stylesheet())
            self.resize(self.default_width, self.default_height)
            self._center_window()
            self._url_input.setFocus(QtCore.Qt.OtherFocusReason)
            # self._url_input.setText("https://")

    def result(self):
        return self._result
    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #     print(self.size())

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
            self._connect_btn.setEnabled(False)
        else:
            self._connect_btn.setEnabled(True)

    def _on_url_enter_press(self):
        self._validate_url()

    def _on_connect_click(self):
        self._validate_url()

    def _on_username_enter_press(self):
        self._password_input.setFocus(QtCore.Qt.OtherFocusReason)

    def _on_password_enter_press(self):
        self._login()

    def _on_change_server_click(self):
        self._go_to_url()

    def _on_login_click(self):
        self._login()

    def _validate_url(self):
        """Use url from input, try connect and change window state on success.

        Todos:
            Change colors of inputs/buttons if connection fails. Maybe add
                some message?
        """

        url = self._url_input.text()
        valid_url = None
        try:
            valid_url = validate_url(url)

        except UrlError as exc:
            parts = ["<b>{}</b>".format(str(exc))]
            for hint in exc.hints:
                parts.append("- {}".format(hint))
            self._set_message("<br/>".join(parts))

        except KeyboardInterrupt:
            # Reraise KeyboardInterrupt error
            raise

        except BaseException:
            # TODO handle any other error
            # - add traceback somewhere
            self._set_message("Unexpected error happened!")

        if valid_url is None:
            return

        self._url_input.setText(valid_url)
        self._go_to_login()

    def _login(self):
        url = self._url_input.text()
        username = self._username_input.text()
        password = self._password_input.text()
        try:
            token = login(url, username, password)
        except Exception as exc:
            print(exc)
            token = None

        if token is not None:
            self._result = (url, token)
            self.close()

    def _set_page(self, page):
        if self._page == page:
            return

        self._page = page
        self._update_visibilities()

    def _go_to_url(self):
        self._set_page(0)
        self._url_input.setFocus(QtCore.Qt.OtherFocusReason)
        self._clear_message()

    def _go_to_login(self):
        self._set_page(1)
        self._username_input.setFocus(QtCore.Qt.OtherFocusReason)
        self._clear_message()

    def _set_message(self, message):
        self._message_label.setText(message)

    def _clear_message(self):
        self._message_label.setText("")

    def _update_visibilities(self):
        self._url_widget.setVisible(self._page == 0)
        self._connect_btn.setVisible(self._page == 0)
        self._login_widget.setVisible(self._page == 1)
        self._login_btn.setVisible(self._page == 1)
        self._change_server_btn.setVisible(self._page == 1)

    def set_url(self, url):
        self._url_input.setText(url)
        self._validate_url()


def ask_to_login(url=None):
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

    if app_instance.startingUp():
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(_exec_window)
        timer.start()
        app_instance.exec_()
    return _exec_window()
