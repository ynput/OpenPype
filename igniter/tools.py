# -*- coding: utf-8 -*-
"""Tools used in **Igniter** GUI."""
import os
from typing import Union
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import platform

import certifi
from pymongo import MongoClient
from pymongo.errors import (
    ServerSelectionTimeoutError,
    InvalidURI,
    ConfigurationError,
    OperationFailure
)


class OpenPypeVersionNotFound(Exception):
    """OpenPype version was not found in remote and local repository."""
    pass


def should_add_certificate_path_to_mongo_url(mongo_url):
    """Check if should add ca certificate to mongo url.

    Since 30.9.2021 cloud mongo requires newer certificates that are not
    available on most of workstation. This adds path to certifi certificate
    which is valid for it. To add the certificate path url must have scheme
    'mongodb+srv' or has 'ssl=true' or 'tls=true' in url query.
    """
    parsed = urlparse(mongo_url)
    query = parse_qs(parsed.query)
    lowered_query_keys = set(key.lower() for key in query.keys())
    add_certificate = False
    # Check if url 'ssl' or 'tls' are set to 'true'
    for key in ("ssl", "tls"):
        if key in query and "true" in query["ssl"]:
            add_certificate = True
            break

    # Check if url contains 'mongodb+srv'
    if not add_certificate and parsed.scheme == "mongodb+srv":
        add_certificate = True

    # Check if url does already contain certificate path
    if add_certificate and "tlscafile" in lowered_query_keys:
        add_certificate = False
    return add_certificate


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

    kwargs = {
        "serverSelectionTimeoutMS": os.environ.get("AVALON_TIMEOUT", 2000)
    }
    # Add certificate path if should be required
    if should_add_certificate_path_to_mongo_url(cnx):
        kwargs["ssl_ca_certs"] = certifi.where()

    try:
        client = MongoClient(cnx, **kwargs)
        client.server_info()
        with client.start_session():
            pass
        client.close()
    except ServerSelectionTimeoutError as e:
        return False, f"Cannot connect to server {cnx} - {e}"
    except ValueError:
        return False, f"Invalid port specified {parsed.port}"
    except (ConfigurationError, OperationFailure, InvalidURI) as exc:
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
    return validate_mongo_connection(mongo)


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
    kwargs = {}
    if should_add_certificate_path_to_mongo_url(url):
        kwargs["ssl_ca_certs"] = certifi.where()

    try:
        # Create mongo connection
        client = MongoClient(url, **kwargs)
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


def get_openpype_path_from_settings(settings: dict) -> Union[str, None]:
    """Get OpenPype path from global settings.

    Args:
        settings (dict): mongodb url.

    Returns:
        path to OpenPype or None if not found
    """
    paths = (
        settings
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


def get_expected_studio_version_str(
    staging=False, global_settings=None
) -> str:
    """Version that should be currently used in studio.

    Args:
        staging (bool): Get current version for staging.
        global_settings (dict): Optional precached global settings.

    Returns:
        str: OpenPype version which should be used. Empty string means latest.
    """
    mongo_url = os.environ.get("OPENPYPE_MONGO")
    if global_settings is None:
        global_settings = get_openpype_global_settings(mongo_url)
    if staging:
        key = "staging_version"
    else:
        key = "production_version"
    return global_settings.get(key) or ""


def load_stylesheet() -> str:
    """Load css style sheet.

    Returns:
        str: content of the stylesheet

    """
    stylesheet_path = Path(__file__).parent.resolve() / "stylesheet.css"

    return stylesheet_path.read_text()


def get_openpype_icon_path() -> str:
    """Path to OpenPype icon png file."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "openpype_icon.png"
    )
