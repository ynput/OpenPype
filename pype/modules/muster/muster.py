import appdirs
from avalon import style
from Qt import QtWidgets
import os
import json
from .widget_login import MusterLogin
from avalon.vendor import requests


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

        def api_callback():
            self.aShowLogin.trigger()

        if "RestApiServer" in modules:
            def api_show_login():
                self.aShowLogin.trigger()
            modules["RestApiServer"].register_callback(
                "/show_login", api_show_login, "muster", "post"
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

        parent.addMenu(self.menu)

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
        MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL")
        if not MUSTER_REST_URL:
            raise AttributeError("Muster REST API url not set")
        params = {
                    'username': username,
                    'password': password
               }
        api_entry = '/api/login'
        response = self._requests_post(
            MUSTER_REST_URL + api_entry, params=params)
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
        self.widget_login.show()

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
            kwargs['verify'] = False if os.getenv("PYPE_DONT_VERIFY_SSL", True) else True  # noqa
        return requests.post(*args, **kwargs)
