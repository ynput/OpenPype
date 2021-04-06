"""Helper functions or classes for Webserver module.

These must not be imported in module itself to not break Python 2
applications.
"""

import inspect
from aiohttp.http_exceptions import HttpBadRequest
from aiohttp.web_exceptions import HTTPMethodNotAllowed
from aiohttp.web_request import Request


DEFAULT_METHODS = ("GET", "POST", "PUT", "DELETE")


class RestApiEndpoint:
    """Helper endpoint class for single endpoint.

    Class can define `get`, `post`, `put` or `delete` async methods for the
    endpoint.
    """
    def __init__(self):
        methods = {}

        for method_name in DEFAULT_METHODS:
            method = getattr(self, method_name.lower(), None)
            if method:
                methods[method_name.upper()] = method

        self.methods = methods

    async def dispatch(self, request: Request):
        method = self.methods.get(request.method.upper())
        if not method:
            raise HTTPMethodNotAllowed("", DEFAULT_METHODS)

        wanted_args = list(inspect.signature(method).parameters.keys())

        available_args = request.match_info.copy()
        available_args["request"] = request

        unsatisfied_args = set(wanted_args) - set(available_args.keys())
        if unsatisfied_args:
            # Expected match info that doesn't exist
            raise HttpBadRequest("")

        return await method(**{
            arg_name: available_args[arg_name]
            for arg_name in wanted_args
        })
