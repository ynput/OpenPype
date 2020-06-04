import os
import re
import inspect
import collections
from .lib import RestMethods
from queue import Queue

from pype.api import Logger

log = Logger().get_logger("RestApiFactory")


def prepare_fullpath(path, prefix):
    """Concatenate registered path and prefix with right form.

    :param path: Registered url path for registered callback.
    :type path: str, list
    :param prefix: Registered and prepared url prefix.
    :type prefix: str, None
    :return: concatenated prefix and path in right form
    :rtype: str
    """

    if isinstance(path, (list, tuple)):
        path_items = path
    else:
        path_items = [part for part in path.split("/") if part]

    fullpath = "/"
    if path and prefix:
        items = [part for part in prefix.split("/") if part]
        items.extend(path_items)
        fullpath = "/".join(items)
        if path.endswith("/"):
            fullpath += "/"

    elif path:
        fullpath = "/".join(path_items)
        if path.endswith("/"):
            fullpath += "/"

    elif prefix:
        fullpath = prefix

    if not fullpath.startswith("/"):
        fullpath = "/{}".format(fullpath)

    return fullpath


def prepare_regex_from_path(full_path, strict_match):
    """Prepare regex based on set path.

    When registered path do not contain dynamic keys regex is not set.
    Dynamic keys are specified with "<" and ">" ("<{dynamic key}>").

    :param full_path: Full url path (prefix + path) for registered callback.
    :type full_path: str, list, None
    :return: regex and keys of all groups in regex
    :rtype: tuple(SRE_Pattern, list), tuple(None, None)
    """
    get_indexes_regex = "<[^< >]+>"
    all_founded_keys = re.findall(get_indexes_regex, full_path)
    if not all_founded_keys:
        return None, None

    regex_path = full_path
    keys = []
    for key in all_founded_keys:
        replacement = "(?P{}\w+)".format(key)
        keys.append(key.replace("<", "").replace(">", ""))
        if not strict_match:
            if full_path.endswith(key):
                replacement = "?{}?".format(replacement)
        regex_path = regex_path.replace(key, replacement)

    regex_path = "^{}$".format(regex_path)

    return re.compile(regex_path), keys


def prepare_prefix(url_prefix):
    """Check if the url_prefix is set and is in correct form.

    Output is None when prefix is empty or "/".

    :param url_prefix: Registered prefix of registered callback.
    :type url_prefix: str, list, None
    :return: Url prefix of registered callback
    :rtype: str, None
    """
    if url_prefix is None or url_prefix.strip() == "/":
        return None
    elif isinstance(url_prefix, (list, tuple)):
        url_prefix = "/".join(url_prefix)
    else:
        items = [part for part in url_prefix.split("/") if part]
        url_prefix = "/".join(items)

    if not url_prefix:
        return None

    while url_prefix.endswith("/"):
        url_prefix = url_prefix[:-1]

    if not url_prefix.startswith("/"):
        url_prefix = "/{}".format(url_prefix)

    return url_prefix


def prepare_methods(methods, callback=None):
    """Check and convert entered methods.

    String `methods` is converted to list. All values are converted to
    `RestMethods` enum object. Invalid methods are ignored and printed out.

    :param methods: Contain rest api methods, when callback is called.
    :type methods: str, list
    :param callback: Registered callback, helps to identify where is
        invalid method.
    :type callback: function, method, optional
    :return: Valid methods
    :rtype: list
    """
    invalid_methods = collections.defaultdict(list)

    if not methods:
        _methods = [RestMethods.GET]
    elif isinstance(methods, str) or isinstance(methods, RestMethods):
        _method = RestMethods.get(methods)
        _methods = []
        if _method is None:
            invalid_methods[methods].append(callback)
        else:
            _methods.append(_method)

    else:
        _methods = []
        for method in methods:
            found = False
            _method = RestMethods.get(method)
            if _method is None:
                invalid_methods[methods].append(callback)
                continue

            _methods.append(_method)

    for method, callbacks in invalid_methods.items():
        callback_info = ""

        callbacks = [cbk for cbk in callbacks if cbk]
        if len(callbacks) > 0:
            multiple_ind = ""
            if len(callbacks) > 1:
                multiple_ind = "s"

            callback_items = []
            for callback in callbacks:
                callback_items.append("\"{}<{}>\"".format(
                    callback.__qualname__, callback.__globals__["__file__"]
                ))

            callback_info = " with callback{} {}".format(
                multiple_ind, "| ".join(callback_items)
            )

        log.warning(
            ("Invalid RestApi method \"{}\"{}").format(method, callback_info)
        )

    return _methods


def prepare_callback_info(callback):
    """Prepare data for callback handling when should be triggered."""
    callback_info = inspect.getfullargspec(callback)

    callback_args = callback_info.args
    callback_args_len = 0
    if callback_args:
        callback_args_len = len(callback_args)
        if type(callback).__name__ == "method":
            callback_args_len -= 1

    defaults = callback_info.defaults
    defaults_len = 0
    if defaults:
        defaults_len = len(defaults)

    annotations = callback_info.annotations

    return {
        "args": callback_args,
        "args_len": callback_args_len,
        "defaults": defaults,
        "defaults_len": defaults_len,
        "hasargs": callback_info.varargs is not None,
        "haskwargs": callback_info.varkw is not None,
        "annotations": annotations
    }


class _RestApiFactory:
    """Factory is used to store and prepare callbacks for requests.

    Should be created only one object used for all registered callbacks when
    it is expected to run only one http server.
    """
    registered_objs = []
    unprocessed_routes = []
    unprocessed_statics = Queue()

    prepared_routes = {
        method: collections.defaultdict(list) for method in RestMethods
    }
    prepared_statics = {}

    has_routes = False

    def has_handlers(self):
        return (self.has_routes or self.prepared_statics)

    def _process_route(self, route):
        return self.unprocessed_routes.pop(
            self.unprocessed_routes.index(route)
        )

    def register_route(
        self, path, callback, url_prefix, methods, strict_match
    ):
        log.debug("Registering callback for item \"{}\"".format(
            callback.__qualname__
        ))
        route = {
            "path": path,
            "callback": callback,
            "url_prefix": url_prefix,
            "methods": methods,
            "strict_match": strict_match
        }
        self.unprocessed_routes.append(route)

    def register_obj(self, obj):
        """Register object for decorated methods in class definition."""
        self.registered_objs.append(obj)

    def register_statics(self, item):
        log.debug("Registering statics path \"{}\"".format(item))
        self.unprocessed_statics.put(item)

    def _prepare_route(self, route):
        """Prepare data of registered callbacks for routes.

        Registration info are prepared to easy filter during handling
        of requests.

        :param route: Contain all necessary info for filtering and
            handling callback for registered route.
        :type route: dict
        """
        callback = route["callback"]
        methods = prepare_methods(route["methods"], callback)
        url_prefix = prepare_prefix(route["url_prefix"])
        fullpath = prepare_fullpath(route["path"], url_prefix)
        regex, regex_keys = prepare_regex_from_path(
            fullpath, route["strict_match"]
        )
        callback_info = prepare_callback_info(callback)

        for method in methods:
            self.has_routes = True
            self.prepared_routes[method][url_prefix].append({
                "regex": regex,
                "regex_keys": regex_keys,
                "fullpath": fullpath,
                "callback": callback,
                "callback_info": callback_info
            })

    def prepare_registered(self):
        """Iter through all registered callbacks and statics to prepare them.

        First are processed callbacks registered with decorators in classes by
        registered objects. Remaining callbacks are filtered, it is checked if
        methods has `__self__` or are defined in <locals> (it is expeted they
        do not requise access to object)
        """

        while not self.unprocessed_statics.empty():
            url_prefix, dir_path = self.unprocessed_statics.get()
            dir_path = os.path.normpath(dir_path)
            if not os.path.exists(dir_path):
                log.warning(
                    "Directory path \"{}\" was not found".format(dir_path)
                )
                continue
            url_prefix = prepare_prefix(url_prefix)
            self.prepared_statics[url_prefix] = dir_path

        for obj in self.registered_objs:
            method_names = [
                attr for attr in dir(obj)
                if inspect.ismethod(getattr(obj, attr))
            ]
            for method_name in method_names:
                method = obj.__getattribute__(method_name)
                if not hasattr(method, "restapi"):
                    continue

                if not method.restapi:
                    continue

                for route in list(self.unprocessed_routes):
                    callback = route["callback"]
                    if not (
                        callback.__qualname__ == method.__qualname__ and
                        callback.__module__ == method.__module__ and
                        callback.__globals__["__file__"] == (
                            method.__globals__["__file__"]
                        )
                    ):
                        continue

                    route["callback"] = method
                    self._process_route(route)
                    self._prepare_route(route)
                    break

        for route in list(self.unprocessed_routes):
            callback = route["callback"]
            is_class_method = len(callback.__qualname__.split(".")) != 1
            if is_class_method:
                missing_self = True
                if hasattr(callback, "__self__"):
                    if callback.__self__ is not None:
                        missing_self = False

                if "<locals>" in callback.__qualname__:
                    pass

                elif missing_self:
                    log.warning((
                        "Object of callback \"{}\" from \"{}\" is not"
                        " accessible for api. Register object or"
                        " register callback with already created object"
                        "(not with decorator in class).".format(
                            callback.__qualname__,
                            callback.__globals__["__file__"]
                        )
                    ))
                    continue

                self._prepare_route(route)
                continue

            self._prepare_route(route)
