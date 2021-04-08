import os
import ftrack_api

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


from openpype.lib import OpenPypeSettingsRegistry

USERNAME_KEY = "username"
API_KEY_KEY = "api_key"


def get_ftrack_hostname(ftrack_server=None):
    if not ftrack_server:
        ftrack_server = os.environ["FTRACK_SERVER"]

    if "//" not in ftrack_server:
        ftrack_server = "//" + ftrack_server

    return urlparse(ftrack_server).hostname


def _get_ftrack_secure_key(hostname):
    """Secure item key for entered hostname."""
    return "/".join(("ftrack", hostname))


def get_credentials(ftrack_server=None):
    hostname = get_ftrack_hostname(ftrack_server)
    secure_key = _get_ftrack_secure_key(hostname)

    registry = OpenPypeSettingsRegistry(secure_key)
    return {
        USERNAME_KEY: registry.get_secure_item(USERNAME_KEY, None),
        API_KEY_KEY: registry.get_secure_item(API_KEY_KEY, None)
    }


def save_credentials(username, api_key, ftrack_server=None):
    hostname = get_ftrack_hostname(ftrack_server)
    secure_key = _get_ftrack_secure_key(hostname)

    registry = OpenPypeSettingsRegistry(secure_key)
    registry.set_secure_item(USERNAME_KEY, username)
    registry.set_secure_item(API_KEY_KEY, api_key)


def clear_credentials(ftrack_server=None):
    hostname = get_ftrack_hostname(ftrack_server)
    secure_key = _get_ftrack_secure_key(hostname)

    registry = OpenPypeSettingsRegistry(secure_key)
    registry.delete_secure_item(USERNAME_KEY)
    registry.delete_secure_item(API_KEY_KEY)


def check_credentials(username, api_key, ftrack_server=None):
    if not ftrack_server:
        ftrack_server = os.environ["FTRACK_SERVER"]

    if not username or not api_key:
        return False

    try:
        session = ftrack_api.Session(
            server_url=ftrack_server,
            api_key=api_key,
            api_user=username
        )
        session.close()

    except Exception:
        return False
    return True
