from http import HTTPStatus

from .lib import (
    RestApiFactory, Splitter,
    ObjAlreadyExist, AbortException,
)


def route(path, url_prefix="", methods=[], strict_match=False):
    """Decorator that register callback and all its attributes.
    Callback is registered to Singleton RestApiFactory.

    :param path: Specify url path when callback should be triggered.
    :type path: str
    :param url_prefix: Specify prefix of path, defaults to "/".
    :type url_prefix: str, list, optional
    :param methods: Specify request method (GET, POST, PUT, etc.) when
        callback will be triggered, defaults to ["GET"]
    :type methods: list, str, optional
    :param strict_match: Decides if callback can handle both single and
        multiple entities (~/projects/<project_name> && ~/projects/),
        defaults to False.
    :type strict_match: bool

    `path` may include dynamic keys that will be stored to object which can
    be obtained in callback.
    Example:
    - registered path: "/projects/<project_name>"
    - url request path: "/projects/S001_test_project"
    In this case will be callback triggered and in accessible data will be
    stored {"project_name": "S001_test_project"}.

    `url_prefix` is optional but it is better to specify for easier filtering
    of requests.
    Example:
    - url_prefix: `"/avalon"` or `["avalon"]`
    - path: `"/projects"`
    In this case request path must be "/avalon/projects" to trigger registered
    callback.
    """

    def decorator(callback):
        RestApiFactory.register_route(
            path, callback, url_prefix, methods, strict_match
        )
        callback.restapi = True
        return callback
    return decorator


def register_statics(url_prefix, dir_path):
    """Decorator that register callback and all its attributes.
    Callback is registered to Singleton RestApiFactory.

    :param url_prefix: Specify prefix of path, defaults to "/".
        (Example: "/resources")
    :type url_prefix: str
    :param dir_path: Path to file folder where statics are located.
    :type dir_path: str
    """

    RestApiFactory.register_statics((url_prefix, dir_path))


def abort(status_code=HTTPStatus.NOT_FOUND, message=None):
    """Should be used to stop registered callback.
    `abort` raise AbortException that is handled with request Handler which
    returns entered status and may send optional message in body.

    :param status_code: Status that will be send in reply of request,
        defaults to 404
    :type status_code: int
    :param message: Message to send in body, default messages are based on
        statuc_code in Handler, defaults to None
    :type message: str, optional
    ...
    :raises AbortException: This exception is handled in Handler to know
        about launched `abort`
    """

    items = []
    items.append(str(status_code))
    if not message:
        message = ""

    items.append(message)

    raise AbortException(Splitter.join(items))


class RestApi:
    """Base class for RestApi classes.

    Use this class is required when it is necessary to have class for handling
    requests and want to use decorators for registering callbacks.

    It is possible to use decorators in another class only when object,
    of class where decorators are, is registered to RestApiFactory.
    """

    def route(path, url_prefix="", methods=[], strict_match=False):
        return route(path, url_prefix, methods, strict_match)

    @classmethod
    def register_route(
        cls, callback, path, url_prefix="", methods=[], strict_match=False
    ):
        return route(path, methods, url_prefix, strict_match)(callback)

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
