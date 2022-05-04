"""Wrapper around interactions with the database"""

import sys
import logging
import functools

from . import schema
from .mongodb import AvalonMongoDB, session_data_from_environment

module = sys.modules[__name__]

Session = {}
_is_installed = False
_connection_object = AvalonMongoDB(Session)
_mongo_client = None
_database = database = None

log = logging.getLogger(__name__)


def install():
    """Establish a persistent connection to the database"""
    if module._is_installed:
        return

    session = session_data_from_environment(context_keys=True)

    session["schema"] = "openpype:session-3.0"
    try:
        schema.validate(session)
    except schema.ValidationError as e:
        # TODO(marcus): Make this mandatory
        log.warning(e)

    _connection_object.Session.update(session)
    _connection_object.install()

    module._mongo_client = _connection_object.mongo_client
    module._database = module.database = _connection_object.database

    module._is_installed = True


def uninstall():
    """Close any connection to the database"""
    module._mongo_client = None
    module._database = module.database = None
    module._is_installed = False
    try:
        module._connection_object.uninstall()
    except AttributeError:
        pass


def requires_install(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        if not _is_installed:
            install()
        return func(*args, **kwargs)
    return decorated


@requires_install
def projects(*args, **kwargs):
    return _connection_object.projects(*args, **kwargs)


@requires_install
def insert_one(doc, *args, **kwargs):
    return _connection_object.insert_one(doc, *args, **kwargs)


@requires_install
def insert_many(docs, *args, **kwargs):
    return _connection_object.insert_many(docs, *args, **kwargs)


@requires_install
def update_one(*args, **kwargs):
    return _connection_object.update_one(*args, **kwargs)


@requires_install
def update_many(*args, **kwargs):
    return _connection_object.update_many(*args, **kwargs)


@requires_install
def replace_one(*args, **kwargs):
    return _connection_object.replace_one(*args, **kwargs)


@requires_install
def replace_many(*args, **kwargs):
    return _connection_object.replace_many(*args, **kwargs)


@requires_install
def delete_one(*args, **kwargs):
    return _connection_object.delete_one(*args, **kwargs)


@requires_install
def delete_many(*args, **kwargs):
    return _connection_object.delete_many(*args, **kwargs)


@requires_install
def find(*args, **kwargs):
    return _connection_object.find(*args, **kwargs)


@requires_install
def find_one(*args, **kwargs):
    return _connection_object.find_one(*args, **kwargs)


@requires_install
def distinct(*args, **kwargs):
    return _connection_object.distinct(*args, **kwargs)


@requires_install
def aggregate(*args, **kwargs):
    return _connection_object.aggregate(*args, **kwargs)


@requires_install
def save(*args, **kwargs):
    return _connection_object.save(*args, **kwargs)


@requires_install
def drop(*args, **kwargs):
    return _connection_object.drop(*args, **kwargs)


@requires_install
def parenthood(*args, **kwargs):
    return _connection_object.parenthood(*args, **kwargs)


@requires_install
def bulk_write(*args, **kwargs):
    return _connection_object.bulk_write(*args, **kwargs)
