import warnings
import functools
from openpype.client.mongo import (
    MongoEnvNotSet,
    OpenPypeMongoConnection,
)


class MongoDeprecatedWarning(DeprecationWarning):
    pass


def mongo_deprecated(func):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter("always", MongoDeprecatedWarning)
        warnings.warn(
            (
                "Call to deprecated function '{}'."
                " Function was moved to 'openpype.client.mongo'."
            ).format(func.__name__),
            category=MongoDeprecatedWarning,
            stacklevel=2
        )
        return func(*args, **kwargs)
    return new_func


@mongo_deprecated
def get_default_components():
    from openpype.client.mongo import get_default_components

    return get_default_components()


@mongo_deprecated
def should_add_certificate_path_to_mongo_url(mongo_url):
    from openpype.client.mongo import should_add_certificate_path_to_mongo_url

    return should_add_certificate_path_to_mongo_url(mongo_url)


@mongo_deprecated
def validate_mongo_connection(mongo_uri):
    from openpype.client.mongo import validate_mongo_connection

    return validate_mongo_connection(mongo_uri)


__all__ = (
    "MongoEnvNotSet",
    "OpenPypeMongoConnection",
    "get_default_components",
    "should_add_certificate_path_to_mongo_url",
    "validate_mongo_connection",
)
