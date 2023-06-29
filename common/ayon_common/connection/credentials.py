"""Handle credentials and connection to server for client application.

Cache and store used server urls. Store/load API keys to/from keyring if
needed. Store metadata about used urls, usernames for the urls and when was
the connection with the username established.

On bootstrap is created global connection with information about site and
client version. The connection object lives in 'ayon_api'.
"""

import os
import json
import platform
import datetime
import contextlib
import subprocess
import tempfile
from typing import Optional, Union, Any

import ayon_api

from ayon_api.constants import SERVER_URL_ENV_KEY, SERVER_API_ENV_KEY
from ayon_api.exceptions import UrlError
from ayon_api.utils import (
    validate_url,
    is_token_valid,
    logout_from_server,
)

from ayon_common.utils import (
    get_ayon_appdirs,
    get_local_site_id,
    get_ayon_launch_args,
)


class ChangeUserResult:
    def __init__(
        self, logged_out, old_url, old_token, old_username,
        new_url, new_token, new_username
    ):
        shutdown = logged_out
        restart = new_url is not None and new_url != old_url
        token_changed = new_token is not None and new_token != old_token

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
    return get_ayon_appdirs("used_servers.json")


def get_servers_info_data():
    """Metadata about used server on this machine.

    Store data about all used server urls, last used url and user username for
    the url. Using this metadata we can remember which username was used per
    url if token stored in keyring loose lifetime.

    Returns:
        dict[str, Any]: Information about servers.
    """

    data = {}
    servers_info_path = _get_servers_path()
    if not os.path.exists(servers_info_path):
        dirpath = os.path.dirname(servers_info_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        return data

    with open(servers_info_path, "r") as stream:
        with contextlib.suppress(BaseException):
            data = json.load(stream)
    return data


def add_server(url: str, username: str):
    """Add server to server info metadata.

    This function will also mark the url as last used url on the machine so on
    next launch will be used.

    Args:
        url (str): Server url.
        username (str): Name of user used to log in.
    """

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


def remove_server(url: str):
    """Remove server url from servers information.

    This should be used on logout to completelly loose information about server
    on the machine.

    Args:
        url (str): Server url.
    """

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


def get_last_server(
    data: Optional[dict[str, Any]] = None
) -> Union[str, None]:
    """Last server used to log in on this machine.

    Args:
        data (Optional[dict[str, Any]]): Prepared server information data.

    Returns:
        Union[str, None]: Last used server url.
    """

    if data is None:
        data = get_servers_info_data()
    return data.get("last_server")


def get_last_username_by_url(
    url: str,
    data: Optional[dict[str, Any]] = None
) -> Union[str, None]:
    """Get last username which was used for passed url.

    Args:
        url (str): Server url.
        data (Optional[dict[str, Any]]): Servers info.

    Returns:
         Union[str, None]: Username.
    """

    if not url:
        return None

    if data is None:
        data = get_servers_info_data()

    if urls := data.get("urls"):
        if url_info := urls.get(url):
            return url_info.get("username")
    return None


def get_last_server_with_username():
    """Receive last server and username used in last connection.

    Returns:
        tuple[Union[str, None], Union[str, None]]: Url and username.
    """

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

        except Exception as exc:
            raise NotImplementedError(
                "Python module `keyring` is not available."
            ) from exc

        # hack for cx_freeze and Windows keyring backend
        if platform.system().lower() == "windows":
            from keyring.backends import Windows

            keyring.set_keyring(Windows.WinVaultKeyring())

        self._url = url
        self._keyring_key = f"AYON/{url}"

    def get_value(self):
        import keyring

        return keyring.get_password(self._keyring_key, self.username_key)

    def set_value(self, value):
        import keyring

        if value is not None:
            keyring.set_password(self._keyring_key, self.username_key, value)
            return

        with contextlib.suppress(keyring.errors.PasswordDeleteError):
            keyring.delete_password(self._keyring_key, self.username_key)


def load_token(url: str) -> Union[str, None]:
    """Get token for url from keyring.

    Args:
        url (str): Server url.

    Returns:
        Union[str, None]: Token for passed url available in keyring.
    """

    return TokenKeyring(url).get_value()


def store_token(url: str, token: str):
    """Store token by url to keyring.

    Args:
        url (str): Server url.
        token (str): User token to server.
    """

    TokenKeyring(url).set_value(token)


def ask_to_login_ui(
    url: Optional[str] = None,
    always_on_top: Optional[bool] = False
) -> tuple[str, str, str]:
    """Ask user to login using UI.

    This should be used only when user is not yet logged in at all or available
    credentials are invalid. To change credentials use 'change_user_ui'
    function.

    Use a subprocess to show UI.

    Args:
        url (Optional[str]): Server url that could be prefilled in UI.
        always_on_top (Optional[bool]): Window will be drawn on top of
            other windows.

    Returns:
        tuple[str, str, str]: Url, user's token and username.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    ui_dir = os.path.join(current_dir, "ui")

    if url is None:
        url = get_last_server()
    username = get_last_username_by_url(url)
    data = {
        "url": url,
        "username": username,
        "always_on_top": always_on_top,
    }

    with tempfile.TemporaryFile(
        mode="w", prefix="ayon_login", suffix=".json", delete=False
    ) as tmp:
        output = tmp.name
        json.dump(data, tmp)

    code = subprocess.call(
        get_ayon_launch_args(ui_dir, "--skip-bootstrap", output))
    if code != 0:
        raise RuntimeError("Failed to show login UI")

    with open(output, "r") as stream:
        data = json.load(stream)
    os.remove(output)
    return data["output"]


def change_user_ui() -> ChangeUserResult:
    """Change user using UI.

    Show UI to user where he can change credentials or url. Output will contain
    all information about old/new values of url, username, api key. If user
    confirmed or declined values.

    Returns:
         ChangeUserResult: Information about user change.
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


def change_token(
    url: str,
    token: str,
    username: Optional[str] = None,
    old_url: Optional[str] = None
):
    """Change url and token in currently running session.

    Function can also change server url, in that case are previous credentials
    NOT removed from cache.

    Args:
        url (str): Url to server.
        token (str): New token to be used for url connection.
        username (Optional[str]): Username of logged user.
        old_url (Optional[str]): Previous url. Value from 'get_last_server'
            is used if not entered.
    """

    if old_url is None:
        old_url = get_last_server()
    if old_url and old_url == url:
        remove_url_cache(old_url)

    # TODO check if ayon_api is already connected
    add_server(url, username)
    store_token(url, token)
    ayon_api.change_token(url, token)


def remove_url_cache(url: str):
    """Clear cache for server url.

    Args:
        url (str): Server url which is removed from cache.
    """

    store_token(url, None)


def remove_token_cache(url: str, token: str):
    """Remove token from local cache of url.

    Is skipped if cached token under the passed url is not the same
    as passed token.

    Args:
        url (str): Url to server.
        token (str): Token to be removed from url cache.
    """

    if load_token(url) == token:
        remove_url_cache(url)


def logout(url: str, token: str):
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
    'AYON_SERVER_URL' and 'AYON_API_KEY'.

    Server is looked up from environment. Already set environent is not
    changed. If environemnt is not filled then last server stored in appdirs
    is used.

    Token is skipped if url is not available. Otherwise, is also checked from
    env and if is not available then uses 'load_token' to try to get token
    based on server url.
    """

    server_url = os.environ.get(SERVER_URL_ENV_KEY)
    if not server_url:
        server_url = get_last_server()
        if not server_url:
            return
        os.environ[SERVER_URL_ENV_KEY] = server_url

    if not os.environ.get(SERVER_API_ENV_KEY):
        if token := load_token(server_url):
            os.environ[SERVER_API_ENV_KEY] = token


def set_environments(url: str, token: str):
    """Change url and token environemnts in currently running process.

    Args:
        url (str): New server url.
        token (str): User's token.
    """

    ayon_api.set_environments(url, token)


def create_global_connection():
    """Create global connection with site id and client version.


    Make sure the global connection in 'ayon_api' have entered site id and
    client version.
    """

    if hasattr(ayon_api, "create_connection"):
        ayon_api.create_connection(
            get_local_site_id(), os.environ.get("AYON_VERSION")
        )


def need_server_or_login() -> bool:
    """Check if server url or login to the server are needed.

    It is recommended to call 'load_environments' on startup before this check.
    But in some cases this function could be called after startup.

    Returns:
        bool: 'True' if server and token are available. Otherwise 'False'.
    """

    server_url = os.environ.get(SERVER_URL_ENV_KEY)
    if not server_url:
        return True

    try:
        server_url = validate_url(server_url)
    except UrlError:
        return True

    token = os.environ.get(SERVER_API_ENV_KEY)
    if token:
        return not is_token_valid(server_url, token)

    token = load_token(server_url)
    if token:
        return not is_token_valid(server_url, token)
    return True


def confirm_server_login(url, token, username):
    """Confirm login of user and do necessary stepts to apply changes.

    This should not be used on "change" of user but on first login.

    Args:
        url (str): Server url where user authenticated.
        token (str): API token used for authentication to server.
        username (Union[str, None]): Username related to API token.
    """

    add_server(url, username)
    store_token(url, token)
    set_environments(url, token)
    create_global_connection()
