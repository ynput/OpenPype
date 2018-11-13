import os
import sys
import requests
import argparse
from pprint import pprint
from PyQt5 import QtCore, QtWidgets
from app import style
from . import credentials, login_tools


class Login_Dialog(QtWidgets.QWidget):

    loginSignal = QtCore.pyqtSignal(object, object, object)
    _login_server_thread = None

    def __init__(self):
        super().__init__()
        self.loginSignal.connect(self.loginWithCredentials)

    def run(self):
        try:
            url = os.getenv('FTRACK_SERVER')
        except:
            print("Environment variable 'FTRACK_SERVER' is not set.")
            return

        self.url = self.checkUrl(url)
        self.open_ftrack()

    def open_ftrack(self):
        self.loginWithCredentials(self.url, None, None)

    def checkUrl(self, url):
        url = url.strip('/ ')

        if not url:
            print("Url is empty!")
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
            print('The server URL set in Templates could not be reached.')
            return


        if (
            result.status_code != 200 or 'FTRACK_VERSION' not in result.headers
        ):
            print('The server URL set in Templates is not a valid ftrack server.')
            return

        return url

    def loginWithCredentials(self, url, username, apiKey):
        url = url.strip('/ ')
        if not url:
            print(
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
            print('The server URL you provided could not be reached.')
            return


        if (
            result.status_code != 200 or 'FTRACK_VERSION' not in result.headers
        ):
            print('The server URL you provided is not a valid ftrack server.')
            return

        # If there is an existing server thread running we need to stop it.
        if self._login_server_thread:
            self._login_server_thread.quit()
            self._login_server_thread = None

        # If credentials are not properly set, try to get them using a http
        # server.
        if not username or not apiKey:
            self._login_server_thread = login_tools.LoginServerThread()
            self._login_server_thread.loginSignal.connect(self.loginSignal)
            self._login_server_thread.start(url)

        verification = credentials._check_credentials(username, apiKey)

        if verification is True:
            credentials._save_credentials(username, apiKey)
            credentials._set_env(username, apiKey)
            self.close()


def run_login():
    app = QtWidgets.QApplication(sys.argv)
    applogin = Login_Dialog()
    applogin.run()
    app.exec_()

if __name__ == '__main__':
    run_login()
