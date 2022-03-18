from typing import Tuple, Optional
from urllib.parse import urlparse

import shotgun_api3
from shotgun_api3.shotgun import AuthenticationFault

from openpype.lib import OpenPypeSecureRegistry, OpenPypeSettingsRegistry
from openpype.modules.shotgrid.lib.record import Credentials


def _get_shotgrid_secure_key(hostname: str, key: str) -> str:
    """Secure item key for entered hostname."""
    return f"shotgrid/{hostname}/{key}"


def _get_secure_value_and_registry(
    hostname: str,
    name: str,
) -> Tuple[str, OpenPypeSecureRegistry]:
    key = _get_shotgrid_secure_key(hostname, name)
    registry = OpenPypeSecureRegistry(key)
    return registry.get_item(name, None), registry


def get_shotgrid_hostname(shotgrid_url: str) -> str:

    if not shotgrid_url:
        raise Exception("Shotgrid url cannot be a null")
    valid_shotgrid_url = (
        f"//{shotgrid_url}" if "//" not in shotgrid_url else shotgrid_url
    )
    return urlparse(valid_shotgrid_url).hostname


# Credentials storing function (using keyring)


def get_credentials(shotgrid_url: str) -> Optional[Credentials]:
    hostname = get_shotgrid_hostname(shotgrid_url)
    if not hostname:
        return None
    login_value, _ = _get_secure_value_and_registry(
        hostname,
        Credentials.login_key_prefix(),
    )
    password_value, _ = _get_secure_value_and_registry(
        hostname,
        Credentials.password_key_prefix(),
    )
    return Credentials(login_value, password_value)


def save_credentials(login: str, password: str, shotgrid_url: str):
    hostname = get_shotgrid_hostname(shotgrid_url)
    _, login_registry = _get_secure_value_and_registry(
        hostname,
        Credentials.login_key_prefix(),
    )
    _, password_registry = _get_secure_value_and_registry(
        hostname,
        Credentials.password_key_prefix(),
    )
    clear_credentials(shotgrid_url)
    login_registry.set_item(Credentials.login_key_prefix(), login)
    password_registry.set_item(Credentials.password_key_prefix(), password)


def clear_credentials(shotgrid_url: str):
    hostname = get_shotgrid_hostname(shotgrid_url)
    login_value, login_registry = _get_secure_value_and_registry(
        hostname,
        Credentials.login_key_prefix(),
    )
    password_value, password_registry = _get_secure_value_and_registry(
        hostname,
        Credentials.password_key_prefix(),
    )

    if login_value is not None:
        login_registry.delete_item(Credentials.login_key_prefix())

    if password_value is not None:
        password_registry.delete_item(Credentials.password_key_prefix())


# Login storing function (using json)


def get_local_login() -> Optional[str]:
    reg = OpenPypeSettingsRegistry()
    try:
        return str(reg.get_item("shotgrid_login"))
    except Exception:
        return None


def save_local_login(login: str):
    reg = OpenPypeSettingsRegistry()
    reg.set_item("shotgrid_login", login)


def clear_local_login():
    reg = OpenPypeSettingsRegistry()
    reg.delete_item("shotgrid_login")


def check_credentials(
    login: str,
    password: str,
    shotgrid_url: str,
) -> bool:

    if not shotgrid_url or not login or not password:
        return False
    try:
        session = shotgun_api3.Shotgun(
            shotgrid_url,
            login=login,
            password=password,
        )
        session.preferences_read()
        session.close()
    except AuthenticationFault:
        return False
    return True
