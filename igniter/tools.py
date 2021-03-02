# -*- coding: utf-8 -*-
"""Tools used in **Igniter** GUI.

Functions ``compose_url()`` and ``decompose_url()`` are the same as in
``pype.lib`` and they are here to avoid importing pype module before its
version is decided.

"""

import os
import uuid
from typing import Dict, Union
from urllib.parse import urlparse, parse_qs
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
        client = MongoClient(**mongo_args)
        client.server_info()
    except ServerSelectionTimeoutError as e:
        return False, f"Cannot connect to server {cnx} - {e}"
    except ValueError:
        return False, f"Invalid port specified {parsed.port}"
    except InvalidURI as e:
        return False, str(e)
    else:
        return True, "Connection is successful"


def validate_path_string(path: str) -> (bool, str):
    """Validate string if it is acceptable by **Igniter**.

    `path` string can be either regular path, or mongodb url or Pype token.

    Args:
        path (str): String to validate.

    Returns:
        (bool, str):
            True if valid, False if not and in second part of tuple
            the reason why it failed.

    """
    if not path:
        return True, "Empty string"
    parsed = urlparse(path)
    if parsed.scheme == "mongodb":
        return validate_mongo_connection(path)
    # test for uuid
    try:
        uuid.UUID(path)
    except (ValueError, TypeError):
        # not uuid
        if not os.path.exists(path):
            return False, "Path doesn't exist or invalid token"
        return True, "Path exists"
    else:
        # we have pype token
        # todo: implement
        return False, "Not implemented yet"


def load_environments(sections: list = None) -> dict:
    """Load environments from Pype.

    This will load environments from database, process them with
    :mod:`acre` and return them as flattened dictionary.

    Args:
        sections (list, optional): load specific types

    Returns;
        dict of str: loaded and processed environments.

    """
    import acre

    from pype import settings

    all_env = settings.get_environments()
    merged_env = {}

    sections = sections or all_env.keys()

    for section in sections:
        try:
            parsed_env = acre.parse(all_env[section])
        except AttributeError:
            continue
        merged_env = acre.append(merged_env, parsed_env)

    return acre.compute(merged_env, cleanup=True)


def get_pype_path_from_db(url: str) -> Union[str, None]:
    """Get Pype path from database.

    Args:
        url (str): mongodb url.

    Returns:
        path to Pype or None if not found

    """
    try:
        components = decompose_url(url)
    except RuntimeError:
        return None
    mongo_args = {
        "host": compose_url(**components),
        "serverSelectionTimeoutMS": 2000
    }
    port = components.get("port")
    if port is not None:
        mongo_args["port"] = int(port)

    try:
        client = MongoClient(**mongo_args)
    except Exception:
        return None

    db = client.pype
    col = db.settings

    result = col.find_one({"type": "global_settings"}, {"value": 1})
    global_settings = result.get("value")

    return global_settings.get("pype_path", {}).get(platform.system().lower())
