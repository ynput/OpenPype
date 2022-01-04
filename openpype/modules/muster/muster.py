import os
import json
import appdirs
import requests
from openpype.modules import OpenPypeModule
from openpype_interfaces import ITrayModule


class MusterModule(OpenPypeModule, ITrayModule):
    """
    Module handling Muster Render credentials. This will display dialog
    asking for user credentials for Muster if not already specified.
    """
    cred_folder_path = os.path.normpath(
        appdirs.user_data_dir('pype-app', 'pype')
    )
    cred_filename = 'muster_cred.json'

    name = "muster"

    def initialize(self, modules_settings):
        muster_settings = modules_settings[self.name]
        self.enabled = muster_settings["enabled"]
        self.muster_url = muster_settings["MUSTER_REST_URL"]

        self.cred_path = os.path.join(
            self.cred_folder_path, self.cred_filename
        )
        # Tray attributes
        self.widget_login = None
        self.action_show_login = None
        self.rest_api_obj = None

    def get_global_environments(self):
        return {
            "MUSTER_REST_URL": self.muster_url
        }

    def tray_init(self):
        from .widget_login import MusterLogin
        self.widget_login = MusterLogin(self)

    def tray_start(self):
        """Show login dialog if credentials not found."""
        # This should be start of module in tray
        cred = self.load_credentials()
        if not cred:
            self.show_login()

    def tray_exit(self):
        """Nothing special for Muster."""
        return

    # Definition of Tray menu
    def tray_menu(self, parent):
        """Add **change credentials** option to tray menu."""
        from Qt import QtWidgets

        # Menu for Tray App
        menu = QtWidgets.QMenu('Muster', parent)
        menu.setProperty('submenu', 'on')

        # Actions
        self.action_show_login = QtWidgets.QAction(
            "Change login", menu
        )

        menu.addAction(self.action_show_login)
        self.action_show_login.triggered.connect(self.show_login)

        parent.addMenu(menu)

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

    def get_auth_token(self, username, password):
        """
        Authenticate user with Muster and get authToken from server.
        """
        if not self.muster_url:
            raise AttributeError("Muster REST API url not set")
        params = {
            'username': username,
            'password': password
        }
        api_entry = '/api/login'
        response = self._requests_post(
            self.muster_url + api_entry, params=params)
        if response.status_code != 200:
            self.log.error(
                'Cannot log into Muster: {}'.format(response.status_code))
            raise Exception('Cannot login into Muster.')

        try:
            token = response.json()['ResponseData']['authToken']
        except ValueError as e:
            self.log.error('Invalid response from Muster server {}'.format(e))
            raise Exception('Invalid response from Muster while logging in.')

        self.save_credentials(token)

    def save_credentials(self, token):
        """
        Save credentials to JSON file
        """
        data = {
            'token': token
        }

        file = open(self.cred_path, 'w')
        file.write(json.dumps(data))
        file.close()

    def show_login(self):
        """
        Show dialog to enter credentials
        """
        if self.widget_login:
            self.widget_login.show()

    # Webserver module implementation
    def webserver_initialization(self, server_manager):
        """Add routes for Muster login."""
        if self.tray_initialized:
            from .rest_api import MusterModuleRestApi

            self.rest_api_obj = MusterModuleRestApi(self, server_manager)

    def _requests_post(self, *args, **kwargs):
        """ Wrapper for requests, disabling SSL certificate validation if
            DONT_VERIFY_SSL environment variable is found. This is useful when
            Deadline or Muster server are running with self-signed certificates
            and their certificate is not added to trusted certificates on
            client machines.

            WARNING: disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.
        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("OPENPYPE_DONT_VERIFY_SSL", True) else True  # noqa
        return requests.post(*args, **kwargs)
