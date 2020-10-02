# -*- coding: utf-8 -*-
"""Tools used in **Igniter** GUI."""
import os
import uuid
from urllib.parse import urlparse

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


def validate_path_string(path: str) -> (bool, str):
    """Validate string if it is acceptable by Igniter.

    ``path` string can be either regular path, or mongodb url or Pype token.

    Args:
        path (str): String to validate.

    Returns:
        (bool, str): True if valid, False if not and in second part of tuple
            the reason why it failed.

    """
    parsed = urlparse(path)
    if parsed.scheme == "mongodb":
        # we have mongo connection string. Let's try if we can connect.
        client = MongoClient(path, serverSelectionTimeoutMS=1)
        try:
            client.server_info()
        except ServerSelectionTimeoutError:
            return False, "Cannot connect to server"
        else:
            return True, "Connection is successful"

    # test for uuid
    try:
        uuid.UUID(path)
    except ValueError as e:
        # not uuid
        if not os.path.exists(path):
            return False, "Path doesn't exist or invalid token"
        return True, "Path exists"
    else:
        # we have pype token
        # todo: implement
        return False, "Not implemented yet"
