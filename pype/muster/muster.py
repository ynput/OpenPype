import appdirs
from pypeapp import style
from Qt import QtWidgets
import os
import json
from .widget_login import MusterLogin


class MusterModule:
    """
    Module handling Muster Render credentials. This will display dialog
    asking for user credentials for Muster if not already specified.
    """
    cred_folder_path = os.path.normpath(
        appdirs.user_data_dir('pype-app', 'pype')
    )
    cred_filename = 'muster_cred.json'

    def __init__(self, main_parent=None, parent=None):
        self.cred_path = os.path.join(
            self.cred_folder_path, self.cred_filename
        )
        self.main_parent = main_parent
        self.parent = parent
        self.widget_login = MusterLogin(main_parent, self)

    def tray_start(self):
        """
        Show login dialog if credentials not found.
        """
        # This should be start of module in tray
        cred = self.load_credentials()
        if not cred:
            self.show_login()
        else:
            # nothing to do
            pass

    def process_modules(self, modules):
        if "RestApiServer" in modules:
            modules["RestApiServer"].register_callback(
                "muster/show_login", self.show_login, "post"
            )

    # Definition of Tray menu
    def tray_menu(self, parent):
        """
        Add **change credentials** option to tray menu.
        """
        # Menu for Tray App
        self.menu = QtWidgets.QMenu('Muster', parent)
        self.menu.setProperty('submenu', 'on')
        self.menu.setStyleSheet(style.load_stylesheet())

        # Actions
        self.aShowLogin = QtWidgets.QAction(
            "Change login", self.menu
        )

        self.menu.addAction(self.aShowLogin)
        self.aShowLogin.triggered.connect(self.show_login)

        return self.menu

    def load_credentials(self):
        """
        Get credentials from JSON file
        """
        credentials = {}
        try:
            file = open(self.cred_path, 'r')
            credentials = json.load(file)
        except Exception:
            file = open(self.cred_path, 'w+')
        file.close()

        return credentials

    def save_credentials(self, username, password):
        """
        Save credentials to JSON file
        """
        data = {
            'username': username,
            'password': password
        }

        file = open(self.cred_path, 'w')
        file.write(json.dumps(data))
        file.close()

    def show_login(self):
        """
        Show dialog to enter credentials
        """
        self.widget_login.show()
