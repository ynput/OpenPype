import os
import re
import json
import traceback
import http.server
from http import HTTPStatus
from urllib.parse import urlparse

from .lib import (
    RestMethods, CallbackResult,
    UrlData, RequestData, Query, Fragment, Params
)
from .exceptions import AbortException
from . import RestApiFactory, CustomNone, Splitter

from pypeapp import Logger

log = Logger().get_logger("RestApiHandler")
NotSet = CustomNone("NotSet")


class Handler(http.server.SimpleHTTPRequestHandler):
    # TODO fill will necessary statuses
    default_messages = {
        HTTPStatus.BAD_REQUEST: "Bad request",
        HTTPStatus.NOT_FOUND: "Not found"
    }

    statuses = {
        "POST": {
            "OK": 200,
            "CREATED": 201
        },
        "PUT": {
            "OK": 200,
            "NO_CONTENT": 204
        }
    }
    def do_GET(self):
        return self._handle_request(RestMethods.GET)

    def do_POST(self):
        return self._handle_request(RestMethods.POST)

    def do_PUT(self):
        return self._handle_request(RestMethods.PUT)

    def do_DELETE(self):
        return self._handle_request(RestMethods.DELETE)

    def do_PATCH(self):
        return self._handle_request(RestMethods.PATCH)

    def _handle_request(self, rest_method):
        """Because processing is technically the same for now so it is used
        the same way
        """
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if rest_method is RestMethods.GET:
            for prefix, dirpath in RestApiFactory.prepared_statics.items():
                if not path.startswith(prefix):
                    continue
                _path = path[len(prefix):]
                return self._handle_statics(dirpath, _path)

        matching_item = None
        found_prefix = None
        url_prefixes = RestApiFactory.prepared_routes[rest_method]
        for url_prefix, items in url_prefixes.items():
            if matching_item is not None:
                break

            if url_prefix is not None:
                if not path.startswith(url_prefix):
                    continue

                found_prefix = url_prefix

            for item in items:
                regex = item["regex"]
                item_full_path = item["fullpath"]
                if regex is None:
                    if path == item_full_path:
                        item["url_data"] = None
                        matching_item = item
                        break

                else:
                    found = re.match(regex, path)
                    if found:
                        item["url_data"] = found.groupdict()
                        matching_item = item
                        break

        if not matching_item:
            if found_prefix is not None:
                _path = path.replace(found_prefix, "")
                if _path:
                    request_str = " \"{}\"".format(_path)
                else:
                    request_str = ""

                message = "Invalid path request{} for prefix \"{}\"".format(
                    request_str, found_prefix
                )
            else:
                message = "Invalid path request \"{}\"".format(self.path)
            log.debug(message)
            self.send_error(HTTPStatus.BAD_REQUEST, message)

            return

        try:
            log.debug("Triggering callback for path \"{}\"".format(path))

            result = self._handle_callback(matching_item, parsed_url)

            return self._handle_callback_result(result, rest_method)

        except AbortException as exc:
            status_code, message = str(exc).split(Splitter)
            status_code = int(status_code)
            if not message:
                message = self.default_messages.get(
                    status_code, "UnexpectedError"
                )

            self.send_response(status_code)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", len(message))
            self.end_headers()

            self.wfile.write(message.encode())
            return message

        except Exception as exc:
            log_message = "Unexpected Exception was raised (this is bug!)"
            log.error(log_message, exc_info=True)
            replace_helper = 0
            items = [log_message]
            items += traceback.extract_tb(exc.__traceback__).format()
            message = "\n".join(items)

            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", len(message))
            self.end_headers()

            self.wfile.write(message.encode())
            return message


    def _handle_callback_result(self, result, rest_method):
        content_type = "application/json"
        status = HTTPStatus.OK
        success = True
        message = None
        data = None

        body = None
        # TODO better handling of results
        if isinstance(result, CallbackResult):
            status = result.status_code
            body_dict = {}
            for key, value in result.items():
                if value is not None:
                    body_dict[key] = value
            body = json.dumps(body_dict)

        elif result in [None, True]:
            status = HTTPStatus.OK
            success = True
            message = "{} request for \"{}\" passed".format(
                rest_method, self.path
            )

        elif result is False:
            status = HTTPStatus.BAD_REQUEST
            success = False

        elif isinstance(result, (dict, list)):
            status = HTTPStatus.OK
            data = result

        if status == HTTPStatus.NO_CONTENT:
            self.send_response(status)
            self.end_headers()
            return

        if not body:
            body_dict = {"success": success}
            if message:
                body_dict["message"] = message

            if not data:
                data = {}

            body_dict["data"] = data
            body = json.dumps(body_dict)

        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()

        self.wfile.write(body.encode())
        return body

    def _handle_callback(self, item, parsed_url):

        regex = item["regex"]
        regex_keys = item["regex_keys"]

        url_data = None
        if regex_keys:
            url_data = {key: None for key in regex_keys}
            if item["url_data"]:
                for key, value in item["url_data"].items():
                    url_data[key] = value

        in_data = None
        cont_len = self.headers.get("Content-Length")
        if cont_len:
            content_length = int(cont_len)
            in_data_str = self.rfile.read(content_length)
            if in_data_str:
                in_data = json.loads(in_data_str)

        url_data = UrlData(url_data)
        request_data = RequestData(in_data)
        query = Query(parsed_url.query)
        params = Params(parsed_url.params)
        fragment = Fragment(parsed_url.fragment)

        callback = item["callback"]
        callback_info = item["callback_info"]

        _args = callback_info["args"]
        _args_len = callback_info["args_len"]
        _defaults = callback_info["defaults"]
        _defaults_len = callback_info["defaults_len"]
        _has_args = callback_info["hasargs"]
        _has_kwargs = callback_info["haskwargs"]

        _annotations = callback_info["annotations"]

        arg_index = 0
        if type(callback).__name__ == "method":
            arg_index = 1

        _kwargs = {arg: NotSet for arg in _args[arg_index:]}
        _available_kwargs = {
            "url_data": url_data,
            "request_data": request_data,
            "query": query,
            "params": params,
            "fragment": fragment,
            "handler": self
        }
        if not regex:
            _available_kwargs.pop("url_data")

        available_len = len(_available_kwargs)
        if available_len < (_args_len - _defaults_len):
            raise Exception((
                "Callback expects {} required positional arguments but {} are"
                " available {}<{}>"
            ).format(
                _args_len, available_len, callback.__qualname__,
                callback.__globals__.get("__file__", "unknown file")
            ))
        elif available_len < _args_len:
            log.warning((
                "Handler \"{}\" will never fill all args of callback {}<{}>"
            ).format(
                self.__class__.__name__,
                callback.__qualname__,
                callback.__globals__.get("__file__", "unknown file")
            ))

        if _args_len == 0:
            if _has_args:
                return callback(*_available_kwargs.values())
            if _has_kwargs:
                return callback(**_available_kwargs)
            else:
                return callback()

        if _annotations:
            for arg, argtype in _annotations.items():
                if argtype == Query:
                    key = "query"
                elif argtype == Params:
                    key = "params"
                elif argtype == Fragment:
                    key = "fragment"
                elif argtype == Handler:
                    key = "handler"
                elif argtype == UrlData:
                    key = "url_data"
                elif argtype == RequestData:
                    key = "request_data"
                else:
                    continue

                _kwargs[arg] = _available_kwargs[key]
                _available_kwargs[key] = NotSet

        for key1, value1 in _kwargs.items():
            if value1 is not NotSet:
                continue
            has_values = False
            for key2, value2 in _available_kwargs.items():
                if value2 is NotSet:
                    continue
                has_values = True
                _kwargs[key1] = value2
                _available_kwargs[key2] = NotSet
                break

            if not has_values:
                break

        _args = []
        kw_keys = [key for key in _kwargs.keys()]
        for key in kw_keys:
            value = _kwargs.pop(key)
            if value is not NotSet:
                _args.append(value)
                continue

        if _has_args:
            for key, value in _available_kwargs.items():
                if value is NotSet:
                    continue
                _args.append(value)

        elif _has_kwargs:
            for key, value in _available_kwargs.items():
                if value is NotSet:
                    continue
                _kwargs[key] = value

        return callback(*_args, **_kwargs)

    def _handle_statics(self, dirpath, path):
        path = os.path.normpath(dirpath + path)

        ctype = self.guess_type(path)
        try:
            file_obj = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            file_stat = os.fstat(file_obj.fileno())
            # Use browser cache if possible
            if ("If-Modified-Since" in self.headers
                    and "If-None-Match" not in self.headers):
                # compare If-Modified-Since and time of last file modification
                try:
                    ims = http.server.email.utils.parsedate_to_datetime(
                        self.headers["If-Modified-Since"])
                except (TypeError, IndexError, OverflowError, ValueError):
                    # ignore ill-formed values
                    pass
                else:
                    if ims.tzinfo is None:
                        # obsolete format with no timezone, cf.
                        # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        # compare to UTC datetime of last modification
                        last_modif = datetime.datetime.fromtimestamp(
                            file_stat.st_mtime, datetime.timezone.utc)
                        # remove microseconds, like in If-Modified-Since
                        last_modif = last_modif.replace(microsecond=0)

                        if last_modif <= ims:
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            file_obj.close()
                            return None

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(file_stat[6]))
            self.send_header("Last-Modified",
            self.date_time_string(file_stat.st_mtime))
            self.end_headers()
            self.wfile.write(file_obj.read())
            return file_obj
        except:
            self.log.error("Failed to read data from file \"{}\"".format(path))
        finally:
            file_obj.close()
