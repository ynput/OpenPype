import os
import ftrack_api

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


from openpype.lib import OpenPypeSecureRegistry

USERNAME_KEY = "username"
API_KEY_KEY = "api_key"


def get_ftrack_hostname(ftrack_server=None):
    if not ftrack_server:
        ftrack_server = os.environ.get("FTRACK_SERVER")

    if not ftrack_server:
        return None

    if "//" not in ftrack_server:
        ftrack_server = "//" + ftrack_server

    return urlparse(ftrack_server).hostname


def _get_ftrack_secure_key(hostname, key):
    """Secure item key for entered hostname."""
    return "/".join(("ftrack", hostname, key))


def get_credentials(ftrack_server=None):
    output = {
        USERNAME_KEY: None,
        API_KEY_KEY: None
    }
    hostname = get_ftrack_hostname(ftrack_server)
    if not hostname:
        return output

    username_name = _get_ftrack_secure_key(hostname, USERNAME_KEY)
    api_key_name = _get_ftrack_secure_key(hostname, API_KEY_KEY)

    username_registry = OpenPypeSecureRegistry(username_name)
    api_key_registry = OpenPypeSecureRegistry(api_key_name)

    output[USERNAME_KEY] = username_registry.get_item(USERNAME_KEY, None)
    output[API_KEY_KEY] = api_key_registry.get_item(API_KEY_KEY, None)

    return output


def save_credentials(username, api_key, ftrack_server=None):
    hostname = get_ftrack_hostname(ftrack_server)
    username_name = _get_ftrack_secure_key(hostname, USERNAME_KEY)
    api_key_name = _get_ftrack_secure_key(hostname, API_KEY_KEY)

    # Clear credentials
    clear_credentials(ftrack_server)

    username_registry = OpenPypeSecureRegistry(username_name)
    api_key_registry = OpenPypeSecureRegistry(api_key_name)

    username_registry.set_item(USERNAME_KEY, username)
    api_key_registry.set_item(API_KEY_KEY, api_key)


def clear_credentials(ftrack_server=None):
    hostname = get_ftrack_hostname(ftrack_server)
    username_name = _get_ftrack_secure_key(hostname, USERNAME_KEY)
    api_key_name = _get_ftrack_secure_key(hostname, API_KEY_KEY)

    username_registry = OpenPypeSecureRegistry(username_name)
    api_key_registry = OpenPypeSecureRegistry(api_key_name)

    current_username = username_registry.get_item(USERNAME_KEY, None)
    current_api_key = api_key_registry.get_item(API_KEY_KEY, None)

    if current_username is not None:
        username_registry.delete_item(USERNAME_KEY)

    if current_api_key is not None:
        api_key_registry.delete_item(API_KEY_KEY)


def check_credentials(username, api_key, ftrack_server=None):
    if not ftrack_server:
        ftrack_server = os.environ.get("FTRACK_SERVER")

    if not ftrack_server or not username or not api_key:
        return False

    user_exists = False
    try:
        session = ftrack_api.Session(
            server_url=ftrack_server,
            api_key=api_key,
            api_user=username
        )
        # Validated that the username actually exists
        user = session.query("User where username is \"{}\"".format(username))
        user_exists = user is not None
        session.close()

    except Exception:
        pass
    return user_exists
