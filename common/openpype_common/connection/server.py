import os
import requests
from urllib.parse import urlparse
from .credentials import load_token, get_last_server

EXAMPLE_URL = "https://openpype.server.com"


class UrlError(Exception):
    def __init__(self, message, hints=None):
        if hints is None:
            hints = []

        self.hints = hints
        super().__init__(message)


def _try_parse_url(url):
    try:
        return urlparse(url)
    except BaseException:
        return None


def validate_url(url):
    stripperd_url = url.strip()
    if not stripperd_url:
        raise UrlError("Invalid url format", hints=["url seems to be empty"])

    # Not sure if this is good idea?
    modified_url = stripperd_url.rstrip("/")
    parsed_url = _try_parse_url(modified_url)
    universal_hints = [
        "does the url work browser?",
        "example url \"{}\"".format(EXAMPLE_URL)
    ]
    if parsed_url is None:
        raise UrlError(
            "Invalid url format",
            hints=universal_hints
        )

    if not parsed_url.scheme:
        new_url = "https://" + modified_url
        raise UrlError(
            "Invalid url format",
            hints=["did you mean \"{}\"?".format(new_url)]
        )

    try:
        # TODO add validation if the url lead to OpenPype server
        #   - thiw won't validate if the url lead to 'google.com'
        response = requests.get(modified_url)
        return modified_url
    except BaseException:
        pass

    hints = []
    if "/" in parsed_url.path:
        new_path = parsed_url.path.split("/")[0]
        hints.append("did you mean \"{}\"?".format(parsed_url.scheme + new_path))

    raise UrlError(
        "Couldn't connect to server",
        hints=hints + universal_hints
    )


def is_token_valid(url, token):
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


def set_environments():
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


def need_login():
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
