import os
import json
import getpass

import appdirs
from pypeapp import style
from Qt import QtWidgets
from .widget_user import UserWidget


class UserModule:
    cred_folder_path = os.path.normpath(
        appdirs.user_data_dir('pype-app', 'pype')
    )
    cred_filename = 'user_info.json'

    def __init__(self, main_parent=None, parent=None):
        self.cred = None
        self.cred_path = os.path.join(
            self.cred_folder_path, self.cred_filename
        )
        self.main_parent = main_parent
        self.parent = parent

        self.widget_login = UserWidget(self)

        self.load_credentials()

    def tray_start(self):
        """Store credentials to env and preset them to widget"""

        if self.cred:
            username = self.cred.get("username") or ""
            os.environ["PYPE_USERNAME"] = username
            self.widget_login.set_user(username)

    def process_modules(self, modules):
        """ Gives ability to connect with imported modules from TrayManager.

        :param modules: All imported modules from TrayManager
        :type modules: dict
        """

        if "RestApiServer" in modules:
            def api_get_username():
                return self.cred

            def api_show_widget():
                self.action_show_widget.trigger()

            modules["RestApiServer"].register_callback(
                "user_module/username", api_get_username, "get"
            )
            modules["RestApiServer"].register_callback(
                "user_module/show_widget", api_show_widget, "post"
            )

    # Definition of Tray menu
    def tray_menu(self, parent_menu):
        """Add menu or action to Tray(or parent)'s menu"""
        action = QtWidgets.QAction("Username", parent_menu)
        action.triggered.connect(self.show_widget)
        parent_menu.addAction(action)

        self.action_show_widget = action

    def load_credentials(self):
        """Get credentials from JSON file """
        credentials = {}
        try:
            file = open(self.cred_path, "r")
            credentials = json.load(file)
            file.close()

        except FileNotFoundError:
            username = getpass.getuser()
            self.save_credentials(username)

        self.cred = credentials

    def save_credentials(self, username):
        """Save credentials to JSON file"""
        self.cred = {"username": str(username)}
        if username:
            os.environ["PYPE_USERNAME"] = username
            self.widget_login.set_user(username)

        file = open(self.cred_path, "w")
        file.write(json.dumps(self.cred))
        file.close()

    def show_widget(self):
        """Show dialog to enter credentials"""
        self.widget_login.show()
