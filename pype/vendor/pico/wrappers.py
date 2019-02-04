from copy import deepcopy
from werkzeug.wrappers import Response
from werkzeug.exceptions import HTTPException

from . import pragmaticjson as json

try:
    unicode
except NameError:
    unicode = str


class JsonResponse(Response):
    def __init__(self, result=None, json_string=None, *args, **kwargs):
        if json_string:
            kwargs['response'] = json_string
        else:
            kwargs['response'] = json.dumps(result)
        kwargs['content_type'] = u'application/json'
        super(JsonResponse, self).__init__(*args, **kwargs)

    def to_jsonp(self, callback):
        r = deepcopy(self)
        json_string = r.response[0].decode()
        content = u'{callback}({json});'.format(callback=callback, json=json_string)
        r.set_data(content)
        r.content_type = u'text/javascript'
        return r


class JsonErrorResponse(JsonResponse):
    def __init__(self, exception=None, **kwargs):
        result = {}
        if exception:
            if isinstance(exception, HTTPException):
                result = {
                    'name': exception.name,
                    'code': exception.code,
                    'message': exception.description,
                }
            else:
                result = {
                    'name': type(exception).__name__,
                    'code': 500,
                    'message': unicode(exception),
                }
        if hasattr(exception, 'to_dict'):
            data = exception.to_dict()
        else:
            data = result
        data.update(kwargs)
        result['code'] = result.get('code', 500)
        result['name'] = result.get('name', 'Internal Server Error')
        super(JsonErrorResponse, self).__init__(data)
        self.status = '%s %s' % (result['code'], result['name'])
