"""
Pico is a minimalistic HTTP API framework for Python.

Copyright (c) 2012, Fergal Walsh.
License: BSD
"""

from __future__ import unicode_literals

import sys
import traceback
import inspect
import importlib
import logging
import os.path
from io import open
from collections import defaultdict
from functools import partial

from werkzeug.exceptions import HTTPException, NotFound, BadRequest, InternalServerError
from werkzeug.wrappers import Request, Response

from . import pragmaticjson as json
from .decorators import base_decorator
from .wrappers import JsonResponse, JsonErrorResponse

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


try:
    unicode
except NameError:
    unicode = str

__author__ = 'Fergal Walsh'
__version__ = '2.0.4'


registry = defaultdict(dict)


def expose(*args, **kwargs):
    @base_decorator()
    def wrapper(wrapped, args, kwargs, request):
        return wrapped(*args, **kwargs)

    def decorator(func):
        func = wrapper(func)
        registry[func.__module__][func.__name__] = func
        return func
    return decorator


def prehandle(*args, **kwargs):
    def decorator(f):
        sys.modules[f.__module__]._prehandle = f
        return f
    return decorator


class PicoApp(object):

    def __init__(self, debug=False):
        self.debug = debug
        self.registry = defaultdict(dict)
        self.modules = {}
        self.definitions = {}
        self.aliases = {}
        self.url_map = {}
        path = os.path.dirname((inspect.getfile(inspect.currentframe())))
        with open(path + '/pico.min.js') as f:
            self._pico_js = f.read()

    def register_module(self, module, alias=None):
        if type(module) == str:
            module = importlib.import_module(module)
        module_name = module.__name__
        alias = alias or module_name
        self.aliases[module_name] = alias
        self.modules[alias] = module
        self.registry[alias] = registry[module_name]
        self.definitions[alias] = {}
        for func_name, func in self.registry[alias].items():
            self.definitions[alias][func_name] = self.function_definition(func)
        self._build_url_map()

    def _get_alias(self, module_name):
        return self.aliases.get(module_name, module_name)

    def _build_url_map(self):
        self.url_map = {}
        self.url_map['/pico.js'] = self.pico_js
        self.url_map['/'] = self.app_definition_handler
        self.url_map['/picoapp.js'] = partial(self.app_definition_handler, 'pico.loadAppDefinition')
        for module_name in self.registry:
            url = self.module_url(module_name)
            # assign definition response handler to function to urls
            self.url_map[url] = partial(self.module_definition_handler, module_name)
            self.url_map[url + '.js'] = partial(self.module_definition_handler, module_name, 'pico.loadModuleDefinition')
            for func_name, func in self.registry[module_name].items():
                url = self.func_url(func)
                # assign the handler function to the the url
                self.url_map[url] = func

    def module_url(self, module_name, pico_url='/'):
        module_path = module_name.replace('.', '/')
        url = '{pico_url}{module}'.format(module=module_path, pico_url=pico_url)
        return url

    def func_url(self, func, pico_url='/'):
        module_path = self._get_alias(func.__module__).replace('.', '/')
        url = '{pico_url}{module}/{func_name}'.format(module=module_path, func_name=func.__name__, pico_url=pico_url)
        return url

    def app_definition_handler(self, callback=None, _request=None):
        app_def = self.app_definition(pico_url=_request.url_root)
        response = JsonResponse(app_def)
        if callback:
            response = response.to_jsonp(callback)
        return response

    def module_definition_handler(self, module_name, callback=None, _request=None):
        module_def = self.module_definition(module_name, pico_url=_request.url_root)
        response = JsonResponse(module_def)
        if callback:
            response = response.to_jsonp(callback)
        return response

    def app_definition(self, pico_url='/'):
        d = {}
        d['url'] = pico_url
        d['modules'] = []
        for module_name in self.registry:
            d['modules'].append(self.module_definition(module_name, pico_url))
        return d

    def module_definition(self, module_name, pico_url='/'):
        d = {}
        d['name'] = module_name
        d['doc'] = inspect.getdoc(self.modules[module_name])
        d['url'] = self.module_url(module_name, pico_url)
        d['functions'] = []
        for func_name, func in self.registry[module_name].items():
            func_def = dict(self.definitions[module_name][func_name])
            func_def['url'] = self.func_url(func, pico_url)
            d['functions'].append(func_def)
        return d

    def function_definition(self, func, pico_url='/'):
        annotations = dict(func._annotations)
        request_args = set(annotations.pop('request_args', []))
        a = inspect.getargspec(func)
        args = []
        for i, arg_name in enumerate(a.args):
            if arg_name and arg_name != 'self' and arg_name not in request_args:
                arg = {'name': arg_name}
                di = (len(a.defaults or []) - len(a.args)) + i
                if di >= 0:
                    arg['default'] = a.defaults[di]
                args.append(arg)
        d = dict(
            name=func.__name__,
            doc=inspect.getdoc(func),
            url=self.func_url(func, pico_url),
            args=args,
        )
        if a.keywords is not None:
            d['accept_extra_args'] = True
        d.update(annotations)
        return d

    def pico_js(self, **kwargs):
        response = Response(self._pico_js, content_type='text/javascript')
        return response

    def parse_args(self, request):
        # first we take the GET querystring args
        args = _multidict_to_dict(request.args)
        # update and override args with post form data
        args.update(_multidict_to_dict(request.form))
        # try to parse any strings as json
        for k in args:
            if isinstance(args[k], list):
                for i, v in enumerate(args[k]):
                    args[k][i] = self._try_json_load(v)
            else:
                args[k] = self._try_json_load(args[k])
        # update args with files
        args.update(_multidict_to_dict(request.files))
        # update and override args with json data
        if 'application/json' in request.headers.get('content-type', ''):
            data = request.get_data(as_text=True)
            if data:
                args.update(self.json_load(data))
        args['_request'] = request
        return args

    def json_load(self, value):
        return json.loads(value)

    def json_dump(self, value):
        return json.dumps(value)

    def _try_json_load(self, value):
        try:
            return self.json_load(value)
        except ValueError:
            return value

    def dispatch_request(self, request):
        path = request.path
        if len(path) > 1 and path[-1] == '/':
            path = path[:-1]
        request.path = path
        try:
            handler = self.url_map[path]
        except KeyError:
            try:
                path = request.script_root + path
                handler = self.url_map[path]
                request.path = path
            except KeyError:
                return NotFound()
        return self.handle_request(request, handler)

    def check_args(self, handler, kwargs):
        module_name = self._get_alias(handler.__module__)
        func_def = self.definitions[module_name][handler.__name__]
        args = {a['name']: a for a in func_def['args']}
        missing = [k for k in (set(args.keys()) - set(kwargs.keys())) if 'default' not in args[k]]
        extra = [k for k in (set(kwargs.keys()) - set(args.keys())) if k[0] != '_']
        message = ''
        if extra and not func_def.get('accept_extra_args', False):
            message += 'Unexpected parameters: [%s]. ' % ', '.join(extra)
        if missing:
            message += 'Missing required parameters: [%s]. ' % ', '.join(missing)
        if message:
            raise BadRequest(message)

    def prehandle(self, request, kwargs):
        if self.debug and kwargs.pop('_debug', None):
            request.use_debugger = True
        else:
            request.use_debugger = False

        try:
            request.token = request.headers.get('Authorization', '').split('Token ')[-1]
        except Exception:
            request.token = None

    def posthandle(self, request, response):
        pass

    def handle_exception(self, exception, request, **kwargs):
        if isinstance(exception, HTTPException):
            return JsonErrorResponse(exception, **kwargs)
        else:
            logger.exception(exception)
            if request.use_debugger:
                raise
            e = InternalServerError()
            if self.debug:
                _, _, exc_tb = sys.exc_info()
                trace = traceback.extract_tb(exc_tb)
                trace = ['%s:%i in %s: %s' % t for t in trace if '/pico/' not in t[0]]
                del exc_tb
                d = dict(
                    name=type(exception).__name__,
                    message=unicode(exception),
                    stack_trace=trace,
                )
                kwargs['__debug__'] = d
            return JsonErrorResponse(e, **kwargs)

    def handle_request(self, request, handler):
        try:
            kwargs = self.parse_args(request)
            callback = kwargs.pop('_callback', None)
            if hasattr(handler, '__module__') and handler.__module__ in self.aliases:
                module = self.modules.get(self._get_alias(handler.__module__))
                if module and self.prehandle:
                    self.prehandle(request, kwargs)
                if hasattr(module, '_prehandle'):
                    module._prehandle(request, kwargs)
                self.check_args(handler, kwargs)
            result = handler(**kwargs)
            if isinstance(result, Response):
                response = result
            else:
                response = JsonResponse(json_string=self.json_dump(result))
            if callback:
                response = response.to_jsonp(callback)
        except Exception as e:
            response = self.handle_exception(e, request)
        finally:
            self.posthandle(request, response)
        return response

    def wsgi_app(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        request = Request(environ)
        request.app = self
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def _multidict_to_dict(m):
    """ Returns a dict with list values only when a key has multiple values. """
    d = {}
    for k, v in m.lists():
        if len(v) == 1:
            d[k] = v[0]
        else:
            d[k] = v
    return d
