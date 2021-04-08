import os
import json
import ftrack_api
import appdirs
import getpass
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


CONFIG_PATH = os.path.normpath(appdirs.user_data_dir("pype-app", "pype"))
CREDENTIALS_FILE_NAME = "ftrack_cred.json"
CREDENTIALS_PATH = os.path.join(CONFIG_PATH, CREDENTIALS_FILE_NAME)
CREDENTIALS_FOLDER = os.path.dirname(CREDENTIALS_PATH)

if not os.path.isdir(CREDENTIALS_FOLDER):
    os.makedirs(CREDENTIALS_FOLDER)


def get_ftrack_hostname(ftrack_server=None):
    if not ftrack_server:
        ftrack_server = os.environ["FTRACK_SERVER"]

    if "//" not in ftrack_server:
        ftrack_server = "//" + ftrack_server

    return urlparse(ftrack_server).hostname


def get_credentials(ftrack_server=None):
    credentials = {}
    if not os.path.exists(CREDENTIALS_PATH):
        with open(CREDENTIALS_PATH, "w") as file:
            file.write(json.dumps(credentials))
            file.close()
        return credentials

    with open(CREDENTIALS_PATH, "r") as file:
        content = file.read()

    hostname = get_ftrack_hostname(ftrack_server)

    content_json = json.loads(content or "{}")
    credentials = content_json.get(hostname) or {}

    return credentials


def save_credentials(ft_user, ft_api_key, ftrack_server=None):
    hostname = get_ftrack_hostname(ftrack_server)

    with open(CREDENTIALS_PATH, "r") as file:
        content = file.read()

    content_json = json.loads(content or "{}")

    content_json[hostname] = {
        "username": ft_user,
        "api_key": ft_api_key
    }

    # Deprecated keys
    if "username" in content_json:
        content_json.pop("username")
    if "apiKey" in content_json:
        content_json.pop("apiKey")

    with open(CREDENTIALS_PATH, "w") as file:
        file.write(json.dumps(content_json, indent=4))


def clear_credentials(ft_user=None, ftrack_server=None):
    if not ft_user:
        ft_user = os.environ.get("FTRACK_API_USER")

    if not ft_user:
        return

    hostname = get_ftrack_hostname(ftrack_server)
    with open(CREDENTIALS_PATH, "r") as file:
        content = file.read()

    content_json = json.loads(content or "{}")
    if hostname not in content_json:
        content_json[hostname] = {}

    content_json.pop(hostname, None)

    with open(CREDENTIALS_PATH, "w") as file:
        file.write(json.dumps(content_json))


def check_credentials(ft_user, ft_api_key, ftrack_server=None):
    if not ftrack_server:
        ftrack_server = os.environ["FTRACK_SERVER"]

    if not ft_user or not ft_api_key:
        return False

    try:
        session = ftrack_api.Session(
            server_url=ftrack_server,
            api_key=ft_api_key,
            api_user=ft_user
        )
        session.close()

    except Exception:
        return False

    return True
