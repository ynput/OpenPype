# -*- coding: utf-8 -*-
"""Tools used in **Igniter** GUI."""
import sys
import os
import uuid
from pype.lib import decompose_url, compose_url
from urllib.parse import urlparse

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, InvalidURI


def validate_mongo_connection(cnx: str) -> (bool, str):
    """Check if provided mongodb URL is valid.

    Args:
        cnx (str): URL to validate.

    Returns:
        (bool, str): True if ok, False if not and reason in str.

    """
    parsed = urlparse(cnx)
    if parsed.scheme in ["mongodb", "mongodb+srv"]:
        # we have mongo connection string. Let's try if we can connect.
        components = decompose_url(cnx)
        mongo_args = {
            "host": compose_url(**components),
            "serverSelectionTimeoutMS": 1000
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
    else:
        return False, "Not mongodb schema"


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


def load_environments() -> dict:
    """Load environments from Pype.

    This will load environments from database, process them with
    :mod:`acre` and return them as flattened dictionary.

    Returns;
        dict of str: loaded and processed environments.

    """
    try:
        import acre
    except ImportError:
        sys.path.append("repos/acre")
        import acre
    from pype import settings

    all_env = settings.environments()
    merged_env = {}
    for _, v in all_env.items():
        if isinstance(v, dict):
            parsed_env = acre.parse(v)
            merged_env = acre.append(merged_env, parsed_env)

    env = acre.compute(merged_env, cleanup=True)
    return env
