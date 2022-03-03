"""Kitsu credentials functions."""

import os
from typing import Tuple
import gazu

from openpype.lib.local_settings import OpenPypeSecureRegistry


def validate_credentials(
    login: str, password: str, kitsu_url: str = os.environ.get("KITSU_SERVER")
) -> bool:
    """Validate credentials by trying to connect to Kitsu host URL.

    :param login: Kitsu Login
    :param password: Kitsu Password
    :param kitsu_url: Kitsu host URL
    :return: Are credentials valid?
    """
    # Connect to server
    validate_host(kitsu_url)

    # Authenticate
    try:
        gazu.log_in(login, password)
    except gazu.exception.AuthFailedException:
        return False

    return True


def validate_host(kitsu_url: str) -> bool:
    """Validate credentials by trying to connect to Kitsu host URL.

    :param kitsu_url: Kitsu host URL
    :return: Is host valid?
    """
    # Connect to server
    gazu.set_host(kitsu_url)

    # Test host
    if gazu.client.host_is_valid():
        return True
    else:
        raise gazu.exception.HostException(f"Host '{kitsu_url}' is invalid.")


def clear_credentials():
    """Clear credentials in Secure Registry."""
    # Get user registry
    user_registry = OpenPypeSecureRegistry("kitsu_user")

    # Set local settings
    user_registry.delete_item("login")
    user_registry.delete_item("password")


def save_credentials(login: str, password: str):
    """Save credentials in Secure Registry.

    :param login: Kitsu Login
    :param password: Kitsu Password
    """
    # Get user registry
    user_registry = OpenPypeSecureRegistry("kitsu_user")

    # Set local settings
    user_registry.set_item("login", login)
    user_registry.set_item("password", password)


def load_credentials() -> Tuple[str, str]:
    """Load registered credentials.

    :return: Login, Password
    """
    # Get user registry
    user_registry = OpenPypeSecureRegistry("kitsu_user")

    return user_registry.get_item("login", None), user_registry.get_item(
        "password", None
    )


def set_credentials_envs(login: str, password: str):
    """Set environment variables with Kitsu login and password.

    :param login: Kitsu Login
    :param password: Kitsu Password
    """
    os.environ["KITSU_LOGIN"] = login
    os.environ["KITSU_PWD"] = password
