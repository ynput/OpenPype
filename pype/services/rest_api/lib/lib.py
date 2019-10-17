import os
import re
import enum
from http import HTTPStatus
from urllib.parse import urlencode, parse_qs

from pypeapp import Logger

log = Logger().get_logger("RestApiServer")


class RestMethods(enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value

        elif isinstance(other, str):
            return self.value.lower() == other.lower()
        return self.value == other

    def __hash__(self):
        return enum.Enum.__hash__(self)

    @classmethod
    def get(cls, name, default=None):
        for meth in cls:
            if meth == name:
                return meth
        return default


class CustomNone:
    def __init__(self, name):
        self._name = name

    def __bool__(self):
        return False

    def __eq__(self, other):
        if type(other) == type(self):
            if other._name == self._name:
                return True
        return False

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name


class HandlerDict(dict):
    def __init__(self, data=None, *args, **kwargs):
        if not data:
            data = {}
        super().__init__(data, *args, **kwargs)

    def __repr__(self):
        return "<{}> {}".format(self.__class__.__name__, str(dict(self)))

class Params(HandlerDict): pass
class UrlData(HandlerDict): pass
class RequestData(HandlerDict): pass

class Query(HandlerDict):
    def __init__(self, query):
        if isinstance(query, dict):
            pass
        else:
            query = parse_qs(query)
        super().__init__(query)

    def get_string(self):
        return urlencode(dict(self), doseq=True)

class Fragment(HandlerDict):
    def __init__(self, fragment):
        if isinstance(fragment, dict):
            _fragment = fragment
        else:
            _fragment = {}
            for frag in fragment.split("&"):
                if not frag:
                    continue
                items = frag.split("=")

                value = None
                key = items[0]
                if len(items) == 2:
                    value = items[1]
                elif len(items) > 2:
                    value = "=".join(items[1:])

                _fragment[key] = value

        super().__init__(_fragment)

    def get_string(self):
        items = []
        for parts in dict(self).items():
            items.append(
                "=".join([p for p in parts if p])
            )
        return "&".join(items)

class RequestInfo:
    def __init__(
        self, url_data, request_data, query, fragment, params, method, handler
    ):
        self.url_data = UrlData(url_data)
        self.request_data = RequestData(request_data)
        self.query = Query(query)
        self.fragment = Fragment(fragment)
        self.params = Params(params)
        self.method = method
        self.handler = handler

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def __hash__(self):
        return {
            "url_data": self.url_data,
            "request_data": self. request_data,
            "query": self.query,
            "fragment": self.fragment,
            "params": self.params,
            "method": self.method,
            "handler": self.handler
        }


class CallbackResult:
    _data = {}

    def __init__(
        self, status_code=HTTPStatus.OK, success=True, message=None, data=None,
        **kwargs
    ):
        self.status_code = status_code
        self._data = {
            "success": success,
            "message": message,
            "data": data
        }
        for k, v in kwargs.items():
            self._data[k] = v

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        for key in self._data:
            yield key

    def get(self, key, default=None):
        return self._data.get(key, default)

    def items(self):
        return self._data.items()
