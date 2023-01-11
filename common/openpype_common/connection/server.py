import os
from ayon_api.exceptions import UrlError
from ayon_api.utils import (
    validate_url,
    is_token_valid,
    logout_from_server,
)
from .credentials import get_last_server, load_token, remove_token_cache


def logout(url, token):
    """Logout from server and throw token away.

    Args:
        url (str): Url from which should be logged out.
        token (str): Token which should be used to log out.
    """

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

    os.environ["AYON_SERVER_URL"] = url or ""
    os.environ["AYON_TOKEN"] = token or ""


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
