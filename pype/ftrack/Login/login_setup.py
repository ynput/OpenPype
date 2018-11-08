import os
import sys
import login_tools
from PyQt5 import QtCore
import requests


class FtrackLogin(object):

    # loginSignal = QtCore.pyqtSignal(object, object, object)
    #
    # def __init__(self):
    #     self.username = None
    #     self.apiKey = None
    #     self.url = "https://pype.ftrackapp.com"
    #
    #     self._login_server_thread = None
    #     self.loginSignal.connect(self.loginWithCredentials)
    #     self.login()
    #
    # def login(self):
    #     '''Login using stored credentials or ask user for them.'''
    #
    #     credentials = self._get_credentials()
    #     if credentials:
    #         # Try to login.
    #         self.loginWithCredentials(
    #             credentials['server_url'],
    #             credentials['api_user'],
    #             credentials['api_key']
    #         )
    #
    # def setup_session(self):
    #     try:
    #         session = ftrack_api.session()
    #     except Exception as e:
    #         return False
    #     return session
    #
    # def report_session_setup_error(self, error):
    #     msg = (
    #         u'\nAn error occured while starting ftrack: <b>{0}</b>.'.format(error)
    #     )
    #     print(msg)
    #     # self.loginError.emit(msg)
    #
    # def _get_credentials(self):
    #     data = {'server_url':self.url,
    #             'api_user':self.username,
    #             'api_key':self.apiKey
    #     }
    #     return data
    #
    # def _save_credentials(self, url, username, apiKey):
    #     self.url = url
    #     self.username = username
    #     self.apiKey = apiKey
    #
    # def loginWithCredentials(self, url, username, apiKey):
    #     url = url.strip('/ ')
    #
    #     if not url:
    #         self.loginError.emit(
    #             'You need to specify a valid server URL, '
    #             'for example https://server-name.ftrackapp.com'
    #         )
    #         return
    #
    #     if not 'http' in url:
    #         if url.endswith('ftrackapp.com'):
    #             url = 'https://' + url
    #         else:
    #             url = 'https://{0}.ftrackapp.com'.format(url)
    #
    #     try:
    #         result = requests.get(
    #             url,
    #             allow_redirects=False  # Old python API will not work with redirect.
    #         )
    #     except requests.exceptions.RequestException:
    #         self.logger.exception('Error reaching server url.')
    #         self.loginError.emit(
    #             'The server URL you provided could not be reached.'
    #         )
    #         return
    #
    #     if (
    #         result.status_code != 200 or 'FTRACK_VERSION' not in result.headers
    #     ):
    #         self.loginError.emit(
    #             'The server URL you provided is not a valid ftrack server.'
    #         )
    #         return
    #
    #     # If there is an existing server thread running we need to stop it.
    #     if self._login_server_thread:
    #         self._login_server_thread.quit()
    #         self._login_server_thread = None
    #
    #     # If credentials are not properly set, try to get them using a http
    #     # server.
    #     if not username or not apiKey:
    #         self._login_server_thread = _login_tools.LoginServerThread()
    #         self._login_server_thread.loginSignal.connect(self.loginSignal)
    #         self._login_server_thread.start(url)
    #         return
    #
    #     # Set environment variables supported by the old API.
    #     os.environ['FTRACK_SERVER'] = url
    #     os.environ['LOGNAME'] = username
    #     os.environ['FTRACK_APIKEY'] = apiKey
    #
    #     # Set environment variables supported by the new API.
    #     os.environ['FTRACK_API_USER'] = username
    #     os.environ['FTRACK_API_KEY'] = apiKey
    #
    #     # Login using the new ftrack API.
    #     try:
    #         self._session = self._setup_session()
    #     except Exception as error:
    #         self.logger.exception(u'Error during login.:')
    #         self._report_session_setup_error(error)
    #         return
    #
    #     # Store credentials since login was successful.
    #     self._save_credentials(url, username, apiKey)
    #
    #     # Verify storage scenario before starting.
    #     if 'storage_scenario' in self._session.server_information:
    #         storage_scenario = self._session.server_information.get(
    #             'storage_scenario'
    #         )
    #         if storage_scenario is None:
    #             # Hide login overlay at this time since it will be deleted
    #             self.logger.debug('Storage scenario is not configured.')
    #             scenario_widget = _scenario_widget.ConfigureScenario(
    #                 self._session
    #             )
    #             scenario_widget.configuration_completed.connect(
    #                 self.location_configuration_finished
    #             )
    #             self.setCentralWidget(scenario_widget)
    #             self.focus()
    #             return


























    loginError = QtCore.pyqtSignal(object)

    #: Signal when event received via ftrack's event hub.
    eventHubSignal = QtCore.pyqtSignal(object)

    # Login signal.
    loginSignal = QtCore.pyqtSignal(object, object, object)

    def __init__(self, *args, **kwargs):

        # self.logger = logging.getLogger(
        #     __name__ + '.' + self.__class__.__name__
        # )

        self._login_server_thread = None

        self._login_overlay = None
        self.loginSignal.connect(self.loginWithCredentials)
        self.login()


    def _onConnectTopicEvent(self, event):
        '''Generic callback for all ftrack.connect events.

        .. note::
            Events not triggered by the current logged in user will be dropped.

        '''
        if event['topic'] != 'ftrack.connect':
            return

        self._routeEvent(event)

    def logout(self):
        '''Clear stored credentials and quit Connect.'''
        self._clear_qsettings()
        config = ftrack_connect.ui.config.read_json_config()

        config['accounts'] = []
        ftrack_connect.ui.config.write_json_config(config)

        QtWidgets.qApp.quit()

    def _clear_qsettings(self):
        '''Remove credentials from QSettings.'''
        settings = QtCore.QSettings()
        settings.remove('login')

    def _get_credentials(self):
        '''Return a dict with API credentials from storage.'''
        credentials = None

        # Read from json config file.
        json_config = ftrack_connect.ui.config.read_json_config()
        if json_config:
            try:
                data = json_config['accounts'][0]
                credentials = {
                    'server_url': data['server_url'],
                    'api_user': data['api_user'],
                    'api_key': data['api_key']
                }
            except Exception:
                self.logger.debug(
                    u'No credentials were found in config: {0}.'.format(
                        json_config
                    )
                )

        # Fallback on old QSettings.
        if not json_config and not credentials:
            settings = QtCore.QSettings()
            server_url = settings.value('login/server', None)
            api_user = settings.value('login/username', None)
            api_key = settings.value('login/apikey', None)

            if not None in (server_url, api_user, api_key):
                credentials = {
                    'server_url': server_url,
                    'api_user': api_user,
                    'api_key': api_key
                }

        return credentials

    def _save_credentials(self, server_url, api_user, api_key):
        '''Save API credentials to storage.'''
        # Clear QSettings since they should not be used any more.
        self._clear_qsettings()

        # Save the credentials.
        json_config = ftrack_connect.ui.config.read_json_config()

        if not json_config:
            json_config = {}

        # Add a unique id to the config that can be used to identify this
        # machine.
        if not 'id' in json_config:
            json_config['id'] = str(uuid.uuid4())

        json_config['accounts'] = [{
            'server_url': server_url,
            'api_user': api_user,
            'api_key': api_key
        }]

        ftrack_connect.ui.config.write_json_config(json_config)

    def login(self):
        '''Login using stored credentials or ask user for them.'''
        credentials = self._get_credentials()
        self.showLoginWidget()

        if credentials:
            # Try to login.
            self.loginWithCredentials(
                credentials['server_url'],
                credentials['api_user'],
                credentials['api_key']
            )

    def showLoginWidget(self):
        '''Show the login widget.'''
        self._login_overlay = ftrack_connect.ui.widget.overlay.CancelOverlay(
            self.loginWidget,
            message='Signing in'
        )

        self._login_overlay.hide()
        self.setCentralWidget(self.loginWidget)
        self.loginWidget.login.connect(self._login_overlay.show)
        self.loginWidget.login.connect(self.loginWithCredentials)
        self.loginError.connect(self.loginWidget.loginError.emit)
        self.loginError.connect(self._login_overlay.hide)
        self.focus()

        # Set focus on the login widget to remove any focus from its child
        # widgets.
        self.loginWidget.setFocus()
        self._login_overlay.hide()

    def _setup_session(self):
        '''Setup a new python API session.'''
        if hasattr(self, '_hub_thread'):
            self._hub_thread.quit()

        plugin_paths = os.environ.get(
            'FTRACK_EVENT_PLUGIN_PATH', ''
        ).split(os.pathsep)

        plugin_paths.extend(self.pluginHookPaths)

        try:
            session = ftrack_connect.session.get_shared_session(
                plugin_paths=plugin_paths
            )
        except Exception as error:
            raise ftrack_connect.error.ParseError(error)

        # Listen to events using the new API event hub. This is required to
        # allow reconfiguring the storage scenario.
        self._hub_thread = _event_hub_thread.NewApiEventHubThread()
        self._hub_thread.start(session)

        ftrack_api._centralized_storage_scenario.register_configuration(
            session
        )

        return session

    def _report_session_setup_error(self, error):
        '''Format error message and emit loginError.'''
        msg = (
            u'\nAn error occured while starting ftrack-connect: <b>{0}</b>.'
            u'\nPlease check log file for more informations.'
            u'\nIf the error persists please send the log file to:'
            u' support@ftrack.com'.format(error)

        )
        self.loginError.emit(msg)

    def loginWithCredentials(self, url, username, apiKey):
        '''Connect to *url* with *username* and *apiKey*.

        loginError will be emitted if this fails.

        '''
        # Strip all leading and preceeding occurances of slash and space.
        url = url.strip('/ ')

        if not url:
            self.loginError.emit(
                'You need to specify a valid server URL, '
                'for example https://server-name.ftrackapp.com'
            )
            return

        if not 'http' in url:
            if url.endswith('ftrackapp.com'):
                url = 'https://' + url
            else:
                url = 'https://{0}.ftrackapp.com'.format(url)

        try:
            result = requests.get(
                url,
                allow_redirects=False  # Old python API will not work with redirect.
            )
        except requests.exceptions.RequestException:
            self.logger.exception('Error reaching server url.')
            self.loginError.emit(
                'The server URL you provided could not be reached.'
            )
            return

        if (
            result.status_code != 200 or 'FTRACK_VERSION' not in result.headers
        ):
            self.loginError.emit(
                'The server URL you provided is not a valid ftrack server.'
            )
            return

        # If there is an existing server thread running we need to stop it.
        if self._login_server_thread:
            self._login_server_thread.quit()
            self._login_server_thread = None

        # If credentials are not properly set, try to get them using a http
        # server.
        if not username or not apiKey:
            self._login_server_thread = _login_tools.LoginServerThread()
            self._login_server_thread.loginSignal.connect(self.loginSignal)
            self._login_server_thread.start(url)
            return

        # Set environment variables supported by the old API.
        os.environ['FTRACK_SERVER'] = url
        os.environ['LOGNAME'] = username
        os.environ['FTRACK_APIKEY'] = apiKey

        # Set environment variables supported by the new API.
        os.environ['FTRACK_API_USER'] = username
        os.environ['FTRACK_API_KEY'] = apiKey

        # Login using the new ftrack API.
        try:
            self._session = self._setup_session()
        except Exception as error:
            self.logger.exception(u'Error during login.:')
            self._report_session_setup_error(error)
            return

        # Store credentials since login was successful.
        self._save_credentials(url, username, apiKey)

        # Verify storage scenario before starting.
        if 'storage_scenario' in self._session.server_information:
            storage_scenario = self._session.server_information.get(
                'storage_scenario'
            )
            if storage_scenario is None:
                # Hide login overlay at this time since it will be deleted
                self.logger.debug('Storage scenario is not configured.')
                scenario_widget = _scenario_widget.ConfigureScenario(
                    self._session
                )

                self.setCentralWidget(scenario_widget)
                self.focus()
                return
