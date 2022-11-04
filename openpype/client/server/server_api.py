import os
from .constants import (
    SERVER_URL_ENV_KEY,
    SERVER_TOKEN_ENV_KEY,
)
from .server import ServerAPIBase


class ServerAPI(ServerAPIBase):
    """Extended server api which also handles storing tokens and url.

    Created object expect to have set environment variables
    'OPENPYPE_SERVER_URL'. Also is expecting filled 'OPENPYPE_TOKEN'
    but that can be filled afterwards with calling 'login' method.
    """

    def __init__(self):
        url = self.get_url()
        token = self.get_token()

        super(ServerAPI, self).__init__(url, token)

        self.validate_server_availability()
        self.create_session()

    def login(self, username, password):
        """Login to the server or change user.

        If user is the same as current user and token is available the
        login is skipped.
        """

        previous_token = self._access_token
        super(ServerAPI, self).login(username, password)
        if self.has_valid_token and previous_token != self._access_token:
            os.environ[SERVER_TOKEN_ENV_KEY] = self._access_token

    def logout(self):
        if not self._access_token:
            return

        try:
            from openpype_common.connection import logout

            logout(self._base_url, self._access_token)
            self.reset_token()

        except:
            self._logout()

    @staticmethod
    def get_url():
        return os.environ.get(SERVER_URL_ENV_KEY)

    @staticmethod
    def get_token():
        return os.environ.get(SERVER_TOKEN_ENV_KEY)

    @staticmethod
    def set_environments(url, token):
        """Change url and token environemnts in currently running process.

        Args:
            url (str): New server url.
            token (str): User's token.
        """

        os.environ[SERVER_URL_ENV_KEY] = url or ""
        os.environ[SERVER_TOKEN_ENV_KEY] = token or ""


class GlobalContext:
    """Singleton connection holder.

    Goal is to avoid create connection on import which can be dangerous in
    some cases.
    """

    _connection = None

    @classmethod
    def get_server_api_connection(cls):
        if cls._connection is None:
            cls._connection = ServerAPI()
        return cls._connection


def get_server_api_connection():
    """Access to global scope object of ServerAPI.

    This access expect to have set environment variables 'OPENPYPE_SERVER_URL'
    and 'OPENPYPE_TOKEN'.

    Returns:
        ServerAPI: Object of connection to server.
    """

    return GlobalContext.get_server_api_connection()


def get(*args, **kwargs):
    con = get_server_api_connection()
    return con.get(*args, **kwargs)


def post(*args, **kwargs):
    con = get_server_api_connection()
    return con.post(*args, **kwargs)


def put(*args, **kwargs):
    con = get_server_api_connection()
    return con.put(*args, **kwargs)


def patch(*args, **kwargs):
    con = get_server_api_connection()
    return con.patch(*args, **kwargs)


def delete(*args, **kwargs):
    con = get_server_api_connection()
    return con.delete(*args, **kwargs)
