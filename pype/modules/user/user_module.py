import os
import json
import getpass

import appdirs
from Qt import QtWidgets
from .widget_user import UserWidget

from pype.api import Logger


class UserModule:
    cred_folder_path = os.path.normpath(
        appdirs.user_data_dir('pype-app', 'pype')
    )
    cred_filename = 'user_info.json'
    env_name = "PYPE_USERNAME"

    log = Logger().get_logger("UserModule", "user")

    def __init__(self, main_parent=None, parent=None):
        self._callbacks_on_user_change = []
        self.cred = {}
        self.cred_path = os.path.normpath(os.path.join(
            self.cred_folder_path, self.cred_filename
        ))
        self.widget_login = UserWidget(self)

        self.load_credentials()

    def register_callback_on_user_change(self, callback):
        self._callbacks_on_user_change.append(callback)

    def tray_start(self):
        """Store credentials to env and preset them to widget"""
        username = ""
        if self.cred:
            username = self.cred.get("username") or ""

        os.environ[self.env_name] = username
        self.widget_login.set_user(username)

    def get_user(self):
        return self.cred.get("username") or getpass.getuser()

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
                "user/username", api_get_username, "get"
            )
            modules["RestApiServer"].register_callback(
                "user/show_widget", api_show_widget, "post"
            )

    # Definition of Tray menu
    def tray_menu(self, parent_menu):
        """Add menu or action to Tray(or parent)'s menu"""
        action = QtWidgets.QAction("Username", parent_menu)
        action.triggered.connect(self.show_widget)
        parent_menu.addAction(action)
        parent_menu.addSeparator()

        self.action_show_widget = action

    def load_credentials(self):
        """Get credentials from JSON file """
        credentials = {}
        try:
            file = open(self.cred_path, "r")
            credentials = json.load(file)
            file.close()

            self.cred = credentials
            username = credentials.get("username")
            if username:
                self.log.debug("Loaded Username \"{}\"".format(username))
            else:
                self.log.debug("Pype Username is not set")

            return credentials

        except FileNotFoundError:
            return self.save_credentials(getpass.getuser())

        except json.decoder.JSONDecodeError:
            self.log.warning((
                "File where users credentials should be stored"
                " has invalid json format. Loading system username."
            ))
            return self.save_credentials(getpass.getuser())

    def change_credentials(self, username):
        self.save_credentials(username)
        for callback in self._callbacks_on_user_change:
            try:
                callback()
            except Exception:
                self.log.warning(
                    "Failed to execute callback \"{}\".".format(str(callback)),
                    exc_info=True
                )

    def save_credentials(self, username):
        """Save credentials to JSON file, env and widget"""
        if username is None:
            username = ""

        username = str(username).strip()

        self.cred = {"username": username}
        os.environ[self.env_name] = username
        self.widget_login.set_user(username)
        try:
            file = open(self.cred_path, "w")
            file.write(json.dumps(self.cred))
            file.close()
            self.log.debug("Username \"{}\" stored".format(username))
        except Exception:
            self.log.error(
                "Could not store username to file \"{}\"".format(self.cred_path),
                exc_info=True
            )

        return self.cred

    def show_widget(self):
        """Show dialog to enter credentials"""
        self.widget_login.show()
