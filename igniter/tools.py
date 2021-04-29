# -*- coding: utf-8 -*-
"""Tools used in **Igniter** GUI.

Functions ``compose_url()`` and ``decompose_url()`` are the same as in
``openpype.lib`` and they are here to avoid importing OpenPype module before its
version is decided.

"""
import sys
import os
from typing import Dict, Union
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import platform

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, InvalidURI


def decompose_url(url: str) -> Dict:
    """Decompose mongodb url to its separate components.

    Args:
        url (str): Mongodb url.

    Returns:
        dict: Dictionary of components.

    """
    components = {
        "scheme": None,
        "host": None,
        "port": None,
        "username": None,
        "password": None,
        "auth_db": None
    }

    result = urlparse(url)
    if result.scheme is None:
        _url = "mongodb://{}".format(url)
        result = urlparse(_url)

    components["scheme"] = result.scheme
    components["host"] = result.hostname
    try:
        components["port"] = result.port
    except ValueError:
        raise RuntimeError("invalid port specified")
    components["username"] = result.username
    components["password"] = result.password

    try:
        components["auth_db"] = parse_qs(result.query)['authSource'][0]
    except KeyError:
        # no auth db provided, mongo will use the one we are connecting to
        pass

    return components


def compose_url(scheme: str = None,
                host: str = None,
                username: str = None,
                password: str = None,
                port: int = None,
                auth_db: str = None) -> str:
    """Compose mongodb url from its individual components.

    Args:
        scheme (str, optional):
        host (str, optional):
        username (str, optional):
        password (str, optional):
        port (str, optional):
        auth_db (str, optional):

    Returns:
        str: mongodb url

    """

    url = "{scheme}://"

    if username and password:
        url += "{username}:{password}@"

    url += "{host}"
    if port:
        url += ":{port}"

    if auth_db:
        url += "?authSource={auth_db}"

    return url.format(**{
        "scheme": scheme,
        "host": host,
        "username": username,
        "password": password,
        "port": port,
        "auth_db": auth_db
    })


def validate_mongo_connection(cnx: str) -> (bool, str):
    """Check if provided mongodb URL is valid.

    Args:
        cnx (str): URL to validate.

    Returns:
        (bool, str): True if ok, False if not and reason in str.

    """
    parsed = urlparse(cnx)
    if parsed.scheme not in ["mongodb", "mongodb+srv"]:
        return False, "Not mongodb schema"
    # we have mongo connection string. Let's try if we can connect.
    try:
        components = decompose_url(cnx)
    except RuntimeError:
        return False, f"Invalid port specified."

    mongo_args = {
        "host": compose_url(**components),
        "serverSelectionTimeoutMS": 2000
    }
    port = components.get("port")
    if port is not None:
        mongo_args["port"] = int(port)

    try:
        client = MongoClient(cnx)
        client.server_info()
        client.close()
    except ServerSelectionTimeoutError as e:
        return False, f"Cannot connect to server {cnx} - {e}"
    except ValueError:
        return False, f"Invalid port specified {parsed.port}"
    except InvalidURI as e:
        return False, str(e)
    except Exception as exc:
        return False, str(exc)
    else:
        return True, "Connection is successful"


def validate_mongo_string(mongo: str) -> (bool, str):
    """Validate string if it is mongo url acceptable by **Igniter**..

    Args:
        mongo (str): String to validate.

    Returns:
        (bool, str):
            True if valid, False if not and in second part of tuple
            the reason why it failed.

    """
    if not mongo:
        return True, "empty string"
    parsed = urlparse(mongo)
    if parsed.scheme in ["mongodb", "mongodb+srv"]:
        return validate_mongo_connection(mongo)
    return False, "not valid mongodb schema"


def validate_path_string(path: str) -> (bool, str):
    """Validate string if it is path to OpenPype repository.

    Args:
        path (str): Path to validate.


    Returns:
        (bool, str):
            True if valid, False if not and in second part of tuple
            the reason why it failed.

    """
    if not path:
        return False, "empty string"

    if not Path(path).exists():
        return False, "path doesn't exists"

    if not Path(path).is_dir():
        return False, "path is not directory"

    return True, "valid path"


def get_openpype_global_settings(url: str) -> dict:
    """Load global settings from Mongo database.

    We are loading data from database `openpype` and collection `settings`.
    There we expect document type `global_settings`.

    Args:
        url (str): MongoDB url.

    Returns:
        dict: With settings data. Empty dictionary is returned if not found.
    """
    try:
        components = decompose_url(url)
    except RuntimeError:
        return {}
    mongo_kwargs = {
        "host": compose_url(**components),
        "serverSelectionTimeoutMS": 2000
    }
    port = components.get("port")
    if port is not None:
        mongo_kwargs["port"] = int(port)

    try:
        # Create mongo connection
        client = MongoClient(**mongo_kwargs)
        # Access settings collection
        col = client["openpype"]["settings"]
        # Query global settings
        global_settings = col.find_one({"type": "global_settings"}) or {}
        # Close Mongo connection
        client.close()

    except Exception:
        # TODO log traceback or message
        return {}

    return global_settings.get("data") or {}


def get_openpype_path_from_db(url: str) -> Union[str, None]:
    """Get OpenPype path from global settings.

    Args:
        url (str): mongodb url.

    Returns:
        path to OpenPype or None if not found
    """
    global_settings = get_openpype_global_settings(url)
    paths = (
        global_settings
        .get("openpype_path", {})
        .get(platform.system().lower())
    ) or []
    # For cases when `openpype_path` is a single path
    if paths and isinstance(paths, str):
        paths = [paths]

    # Loop over paths and return only existing
    for path in paths:
        if os.path.exists(path):
            return path
    return None
