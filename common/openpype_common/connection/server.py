import os
import requests
from urllib.parse import urlparse
from .credentials import get_last_server, load_token, store_token


class UrlError(Exception):
    def __init__(self, message, title, hints=None):
        if hints is None:
            hints = []

        self.title = title
        self.hints = hints
        super().__init__(message)


def _try_parse_url(url):
    try:
        return urlparse(url)
    except BaseException:
        return None


def _try_connect_to_server(url):
    try:
        # TODO add validation if the url lead to OpenPype server
        #   - thiw won't validate if the url lead to 'google.com'
        requests.get(url)

    except BaseException:
        return False
    return True


def validate_url(url):
    """Validate url if is valid and server is available.

    Validation checks if can be parsed as url and contains scheme.

    Function will try to autofix url thus will return modified url when
    connection to server works.

    ```python
    my_url = "my.server.url"
    try:
        # Store new url
        validated_url = validate_url(my_url)

    except UrlError:
        # Handle invalid url
        ...
    ```

    Args:
        url (str): Server url.

    Returns:
        Url which was used to connect to server.

    Raises:
        UrlError: Error with short description and hints for user.
    """

    stripperd_url = url.strip()
    if not stripperd_url:
        raise UrlError(
            "Invalid url format. Url is empty.",
            title="Invalid url format",
            hints=["url seems to be empty"]
        )

    # Not sure if this is good idea?
    modified_url = stripperd_url.rstrip("/")
    parsed_url = _try_parse_url(modified_url)
    universal_hints = [
        "does the url work in browser?"
    ]
    if parsed_url is None:
        raise UrlError(
            "Invalid url format. Url cannot be parsed as url \"{}\".".format(
                modified_url
            ),
            title="Invalid url format",
            hints=universal_hints
        )

    # Try add 'https://' scheme if is missing
    # - this will trigger UrlError if both will crash
    if not parsed_url.scheme:
        new_url = "https://" + modified_url
        if _try_connect_to_server(new_url):
            return new_url

    if _try_connect_to_server(modified_url):
        return modified_url

    hints = []
    if "/" in parsed_url.path or not parsed_url.scheme:
        new_path = parsed_url.path.split("/")[0]
        if not parsed_url.scheme:
            new_path = "https://" + new_path

        hints.append(
            "did you mean \"{}\"?".format(parsed_url.scheme + new_path)
        )

    raise UrlError(
        "Couldn't connect to server on \"{}\"".format(),
        title="Couldn't connect to server",
        hints=hints + universal_hints
    )


def is_token_valid(url, token):
    """Check if token is valid.

    Args:
        url (str): Server url.
        token (str): User's token.

    Returns:
        bool: True if token is valid.
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(token)
    }
    response = requests.get(
        "{}/api/users/me".format(url),
        headers=headers
    )
    return response.status_code == 200


def login(url, username, password):
    """Use login to the server to receive token.

    Args:
        url (str): Server url.
        username (str): User's username.
        password (str): User's password.

    Returns:
        Union[str, None]: User's token if login was successfull.
            Otherwise 'None'.
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(
        "{}/api/auth/login".format(url),
        headers=headers,
        json={
            "name": username,
            "password": password
        }
    )
    token = None
    # 200 - success
    # 401 - invalid credentials
    # *   - other issues
    if response.status_code == 200:
        token = response.json()["token"]

    return token


def logout(url, token):
    """Logout from server and throw token away.

    Args:
        url (str): Url from which should be logged out.
        token (str): Token which should be used to log out.
    """

    current_token = load_token(url)
    # Remove token from keyring
    if current_token == token:
        store_token(url, None)

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(token)
    }
    requests.post(
        url + "/api/auth/logout",
        headers=headers
    )


def load_environments():
    """Load environments on startup.

    Handle environments needed for connection with server. Environments are
    'OPENPYPE_SERVER_URL' and 'OPENPYPE_TOKEN'.

    Server is looked up from environment. Already set environent is not
    changed. If environemnt is not filled then last server stored in appdirs
    is used.

    Token is skipped if url is not available. Otherwise is also checked from
    env and if is not available then uses 'load_token' to try get token based
    on server url.
    """

    server_url = os.environ.get("OPENPYPE_SERVER_URL")
    if not server_url:
        server_url = get_last_server()
        if not server_url:
            return
        os.environ["OPENPYPE_SERVER_URL"] = server_url

    token = os.environ.get("OPENPYPE_TOKEN")
    if not token:
        token = load_token(server_url)
        if token:
            os.environ["OPENPYPE_TOKEN"] = token


def set_environments(url, token):
    """Change url and token environemnts in currently running process.

    Args:
        url (str): New server url.
        token (str): User's token.
    """

    os.environ["OPENPYPE_SERVER_URL"] = url or ""
    os.environ["OPENPYPE_TOKEN"] = token or ""


def need_server_or_login():
    """Check if server url or login to the server are needed.

    It is recommended to call 'load_environments' on startup before this check.
    But in some cases this function could be called after startup.

    Returns:
        bool: 'True' if server and token are available. Otherwise 'False'.
    """

    server_url = os.environ.get("OPENPYPE_SERVER_URL")
    if not server_url:
        return True

    try:
        server_url = validate_url(server_url)
    except UrlError:
        return True

    token = os.environ.get("OPENPYPE_TOKEN")
    if token:
        return not is_token_valid(server_url, token)

    token = load_token(server_url)
    return not is_token_valid(server_url, token)
