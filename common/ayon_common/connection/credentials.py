import os
import json
import platform
import datetime

import appdirs
import ayon_api

from ayon_api.exceptions import UrlError
from ayon_api.utils import (
    validate_url,
    is_token_valid,
    logout_from_server,
)


def _get_servers_path():
    return os.path.join(
        appdirs.user_data_dir("ayon", "ynput"), "used_servers.json"
    )


def get_servers_info_data():
    data = {}
    servers_info_path = _get_servers_path()
    if not os.path.exists(servers_info_path):
        dirpath = os.path.dirname(servers_info_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        with open(servers_info_path, "w") as stream:
            json.dump(data, stream)
        return data

    with open(servers_info_path, "r") as stream:
        try:
            data = json.load(stream)
        except BaseException:
            pass
    return data


def get_last_server():
    data = get_servers_info_data()
    return data.get("last_server")


def add_server(url):
    servers_info_path = _get_servers_path()
    data = get_servers_info_data()
    data["last_server"] = url
    with open(servers_info_path, "w") as stream:
        json.dump(data, stream)


class TokenKeyring:
    # Fake username with hardcoded username
    username_key = "username"

    def __init__(self, url):
        try:
            import keyring

        except Exception:
            raise NotImplementedError(
                "Python module `keyring` is not available."
            )

        # hack for cx_freeze and Windows keyring backend
        if platform.system().lower() == "windows":
            from keyring.backends import Windows

            keyring.set_keyring(Windows.WinVaultKeyring())

        self._url = url
        self._keyring_key = "AYON/{}".format(url)

    def get_value(self):
        import keyring

        return keyring.get_password(self._keyring_key, self.username_key)

    def set_value(self, value):
        import keyring

        if value is not None:
            keyring.set_password(self._keyring_key, self.username_key, value)
            return

        try:
            keyring.delete_password(self._keyring_key, self.username_key)
        except keyring.errors.PasswordDeleteError:
            pass


def load_token(url):
    return TokenKeyring(url).get_value()


def store_token(url, token):
    TokenKeyring(url).set_value(token)


def ask_to_login_ui(*args, **kwargs):
    from .ui import ask_to_login

    return ask_to_login(*args, **kwargs)


def remove_url_cache(url):
    store_token(url, None)


def remove_token_cache(url, token):
    if load_token(url) == token:
        remove_url_cache(url)


def logout(url, token):
    """Logout from server and throw token away.

    Args:
        url (str): Url from which should be logged out.
        token (str): Token which should be used to log out.
    """

    remove_server(url)
    ayon_api.close_connection()
    ayon_api.set_environments(None, None)
    remove_token_cache(url, token)
    logout_from_server(url, token)


def load_environments():
    """Load environments on startup.

    Handle environments needed for connection with server. Environments are
    'AYON_SERVER_URL' and 'AYON_TOKEN'.

    Server is looked up from environment. Already set environent is not
    changed. If environemnt is not filled then last server stored in appdirs
    is used.

    Token is skipped if url is not available. Otherwise is also checked from
    env and if is not available then uses 'load_token' to try get token based
    on server url.
    """

    server_url = os.environ.get("AYON_SERVER_URL")
    if not server_url:
        server_url = get_last_server()
        if not server_url:
            return
        os.environ["AYON_SERVER_URL"] = server_url

    token = os.environ.get("AYON_TOKEN")
    if not token:
        token = load_token(server_url)
        if token:
            os.environ["AYON_TOKEN"] = token


def set_environments(url, token):
    """Change url and token environemnts in currently running process.

    Args:
        url (str): New server url.
        token (str): User's token.
    """

    ayon_api.set_environments(url, token)


def need_server_or_login():
    """Check if server url or login to the server are needed.

    It is recommended to call 'load_environments' on startup before this check.
    But in some cases this function could be called after startup.

    Returns:
        bool: 'True' if server and token are available. Otherwise 'False'.
    """

    server_url = os.environ.get("AYON_SERVER_URL")
    if not server_url:
        return True

    try:
        server_url = validate_url(server_url)
    except UrlError:
        return True

    token = os.environ.get("AYON_TOKEN")
    if token:
        return not is_token_valid(server_url, token)

    token = load_token(server_url)
    return not is_token_valid(server_url, token)