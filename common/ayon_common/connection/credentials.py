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


class ChangeUserResult:
    def __init__(
        self, logged_out, old_url, old_token, old_username,
        new_url, new_token, new_username
    ):
        shutdown = logged_out
        restart = new_url is not None and new_url != old_url
        token_changed = new_token is not None and new_token == old_token

        self.logged_out = logged_out
        self.old_url = old_url
        self.old_token = old_token
        self.old_username = old_username
        self.new_url = new_url
        self.new_token = new_token
        self.new_username = new_username

        self.shutdown = shutdown
        self.restart = restart
        self.token_changed = token_changed


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


def add_server(url, username):
    servers_info_path = _get_servers_path()
    data = get_servers_info_data()
    data["last_server"] = url
    if "urls" not in data:
        data["urls"] = {}
    data["urls"][url] = {
        "updated_dt": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "username": username,
    }

    with open(servers_info_path, "w") as stream:
        json.dump(data, stream)


def remove_server(url):
    if not url:
        return

    servers_info_path = _get_servers_path()
    data = get_servers_info_data()
    if data.get("last_server") == url:
        data["last_server"] = None

    if "urls" in data:
        data["urls"].pop(url, None)

    with open(servers_info_path, "w") as stream:
        json.dump(data, stream)


def get_last_server(data=None):
    if data is None:
        data = get_servers_info_data()
    return data.get("last_server")


def get_last_username_by_url(url, data=None):
    if not url:
        return None

    if data is None:
        data = get_servers_info_data()

    urls = data.get("urls")
    if urls:
        url_info = urls.get(url)
        if url_info:
            return url_info.get("username")
    return None


def get_last_server_with_username():
    data = get_servers_info_data()
    url = get_last_server(data)
    username = get_last_username_by_url(url)
    return url, username


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


def ask_to_login_ui(url=None):
    from .ui import ask_to_login

    if url is None:
        url = get_last_server()
    username = get_last_username_by_url(url)
    return ask_to_login(url, username)


def change_user_ui():
    """

    Returns:
         Tuple[Union[bool, None], : True if user logged out
    """

    from .ui import change_user

    url, username = get_last_server_with_username()
    token = load_token(url)
    result = change_user(url, username, token)
    new_url, new_token, new_username, logged_out = result

    output = ChangeUserResult(
        logged_out, url, token, username,
        new_url, new_token, new_username
    )
    if output.logged_out:
        logout(url, token)

    elif output.token_changed:
        change_token(
            output.new_url,
            output.new_token,
            output.new_username,
            output.old_url
        )
    return output


def change_token(url, token, username=None, old_url=None):
    if old_url is None:
        old_url = get_last_server()
    if old_url and old_url == url:
        remove_url_cache(old_url)

    # TODO check if ayon_api is already connected
    add_server(url, username)
    store_token(url, token)
    ayon_api.change_token(url, token)


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
