import os
import json
import getpass

from abc import ABCMeta, abstractmethod

import six
import appdirs

from .. import (
    PypeModule,
    ITrayModule
)


@six.add_metaclass(ABCMeta)
class IUserModule:
    """Interface for other modules to use user change callbacks."""

    @abstractmethod
    def on_pype_user_change(self, username):
        """What should happen on Pype user change."""
        pass


class UserModule(PypeModule, ITrayModule):
    cred_folder_path = os.path.normpath(
        appdirs.user_data_dir('pype-app', 'pype')
    )
    cred_filename = 'user_info.json'
    env_name = "PYPE_USERNAME"

    name = "user"

    def initialize(self, modules_settings):
        user_settings = modules_settings[self.name]
        self.enabled = user_settings["enabled"]

        self.callbacks_on_user_change = []
        self.cred = {}
        self.cred_path = os.path.normpath(os.path.join(
            self.cred_folder_path, self.cred_filename
        ))

        # Tray attributes
        self.widget_login = None
        self.action_show_widget = None

    def tray_init(self):
        from .widget_user import UserWidget
        self.widget_login = UserWidget(self)

        self.load_credentials()

    def register_callback_on_user_change(self, callback):
        self.callbacks_on_user_change.append(callback)

    def tray_start(self):
        """Store credentials to env and preset them to widget"""
        username = ""
        if self.cred:
            username = self.cred.get("username") or ""

        os.environ[self.env_name] = username
        self.widget_login.set_user(username)

    def tray_exit(self):
        """Nothing special for User."""
        return

    def get_user(self):
        return self.cred.get("username") or getpass.getuser()

    def connect_with_modules(self, enabled_modules):
        for module in enabled_modules:
            if isinstance(module, IUserModule):
                self.callbacks_on_user_change.append(
                    module.on_pype_user_change
                )

    # Definition of Tray menu
    def tray_menu(self, parent_menu):
        from Qt import QtWidgets
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
        for callback in self.callbacks_on_user_change:
            try:
                callback(username)
            except Exception:
                self.log.warning(
                    "Failed to execute callback \"{}\".".format(
                        str(callback)
                    ),
                    exc_info=True
                )

    def save_credentials(self, username):
        """Save credentials to JSON file, env and widget"""
        if username is None:
            username = ""

        username = str(username).strip()

        self.cred = {"username": username}
        os.environ[self.env_name] = username
        if self.widget_login:
            self.widget_login.set_user(username)
        try:
            file = open(self.cred_path, "w")
            file.write(json.dumps(self.cred))
            file.close()
            self.log.debug("Username \"{}\" stored".format(username))
        except Exception:
            self.log.error(
                "Could not store username to file \"{}\"".format(
                    self.cred_path
                ),
                exc_info=True
            )

        return self.cred

    def show_widget(self):
        """Show dialog to enter credentials"""
        self.widget_login.show()
