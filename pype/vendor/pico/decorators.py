import types

import wrapt

from werkzeug.exceptions import MethodNotAllowed
from werkzeug.wrappers import Response

from . import pragmaticjson as json
from .wrappers import JsonResponse


def base_decorator(annotations={}, *args, **kwargs):
    def _base_decorator(wrapper):
        def _wrapper(wrapped, instance, args, kwargs):
            request = kwargs.get('_request', None)
            if not hasattr(wrapped, '_self_pico_request_decorator'):
                kwargs.pop('_request', None)
            if request:
                return wrapper(wrapped, args, kwargs, request)
            else:
                return wrapped(*args, **kwargs)

        def new_wrapper(f):
            x = wrapt.decorator(_wrapper)(f)
            x._annotations = getattr(x, '_annotations', {})
            x._annotations.update(annotations)
            x._self_pico_request_decorator = True
            return x
        return new_wrapper
    return _base_decorator


def request_args(*args, **kwargs):
    @base_decorator(annotations={'request_args': list(kwargs.keys()) + list(args)})
    def wrapper(wrapped, innerargs, innerkwargs, request):
        if args:
            innerkwargs[args[0]] = request
        for k, v in kwargs.items():
            if isinstance(v, types.FunctionType):
                innerkwargs[k] = v(request)
            else:
                innerkwargs[k] = getattr(request, v)
        return wrapped(*innerargs, **innerkwargs)
    return wrapper


def stream(*args, **kwargs):
    @base_decorator(annotations={'stream': True})
    def wrapper(wrapped, args, kwargs, request):
        result = wrapped(*args, **kwargs)

        def f(stream):
            try:
                for d in stream:
                    yield 'data: ' + json.dumps(d) + '\n\n'
                yield 'event: close\n'
                yield 'data: close\n\n'
            except Exception as e:
                yield 'event: error\n'
                yield 'data: ' + str(e) + '\n\n'
        response = Response(f(result), content_type='text/event-stream')
        return response
    return wrapper


def set_cookie(*args, **kwargs):
    @base_decorator()
    def wrapper(wrapped, innerargs, innerkwargs, request):
        result = wrapped(*innerargs, **innerkwargs)
        response = JsonResponse(result)
        for k, v in result.items():
            response.set_cookie(k, v, **kwargs)
        return response
    return wrapper


def delete_cookie(key, **kwargs):
    @base_decorator()
    def wrapper(wrapped, innerargs, innerkwargs, request):
        result = wrapped(*innerargs, **innerkwargs)
        response = JsonResponse(result)
        response.delete_cookie(key, **kwargs)
        return response
    return wrapper


def protected(protector, annotations={}):
    """
    Decorator for protecting a function.
    The protected function will not be called if the protector raises
     an exception or returns False.
    The protector should have the following signature:
        def protector(request, wrapped, args, kwargs):
            return True
    """
    @base_decorator(annotations)
    def wrapper(wrapped, args, kwargs, request):
        if protector(request, wrapped, args, kwargs) is not False:
            return wrapped(*args, **kwargs)
    return wrapper


def require_method(method):
    def p(request, w, args, kwargs):
        if not request.method == method:
            raise MethodNotAllowed()
    return protected(p, annotations={'method': method})


def cookie(key):
    def accessor(request):
        return request.cookies.get(key)
    return accessor


def header(name):
    def accessor(request):
        return request.headers.get(name)
    return accessor


def basic_auth(name=None):
    def accessor(request):
        if request.authorization:
            auth = request.authorization
            if name is None:
                return (auth.username, auth.password)
            else:
                return getattr(auth, name)
        else:
            return None
    return accessor
