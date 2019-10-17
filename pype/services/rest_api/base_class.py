from functools import wraps
from http import HTTPStatus

from .lib import (
    RestApiFactory, Splitter,
    ObjAlreadyExist, AbortException,
)


def route(path, url_prefix="", methods=[]):
    def decorator(callback):
        RestApiFactory.register_route(path, callback, url_prefix, methods)
        callback.restapi = True
        return callback
    return decorator


def register_statics(url_prefix, dir_path):
    RestApiFactory.register_statics((url_prefix, dir_path))


def abort(status_code=HTTPStatus.NOT_FOUND, message=None):
    items = []
    items.append(str(status_code))
    if not message:
        message = ""

    items.append(message)

    raise AbortException(Splitter.join(items))


class RestApi:
    def route(path, url_prefix="", methods=[]):
        return route(path, url_prefix, methods)

    @classmethod
    def register_route(cls, callback, path, url_prefix="", methods=[]):
        return route(path, methods, url_prefix)(callback)

    @classmethod
    def register_statics(cls, url_prefix, dir_path):
        return register_statics(url_prefix, dir_path)

    @classmethod
    def abort(cls, status_code=HTTPStatus.NOT_FOUND, message=None):
        abort(status_code, message)

    def __new__(cls, *args, **kwargs):
        for obj in RestApiFactory.registered_objs:
            if type(obj) == cls:
                raise ObjAlreadyExist(cls)
        instance = super(RestApi, cls).__new__(cls)
        RestApiFactory.register_obj(instance)
        return instance
