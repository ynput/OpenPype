import json
import decimal
import datetime


json_dumpers = {
    decimal.Decimal: lambda d: str(d)
}

json_loaders = [
    lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(),
    lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'),
    lambda s: datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ')
]

try:
    basestring
except NameError:
    basestring = str


def convert_keys(obj):
    if type(obj) == dict:  # convert non string keys to strings
        return {str(k): convert_keys(obj[k]) for k in obj}
    else:
        return obj


class Encoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        self.json_dumpers = kwargs.pop('json_dumpers', {})
        json.JSONEncoder.__init__(self, *args, **kwargs)

    def default(self, obj):
        if type(obj) in json_dumpers:
            obj = self.json_dumpers[type(obj)](obj)
            obj = convert_keys(obj)
            return obj
        for obj_type, dumper in self.json_dumpers.items():
            if isinstance(obj, obj_type):
                return dumper(obj)
        if hasattr(obj, 'as_json'):
            return obj.as_json()
        if hasattr(obj, 'json'):
            return json.loads(obj.json)
        elif hasattr(obj, 'keys'):
            return dict(obj)
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        elif hasattr(obj, '__iter__'):
            return list(obj)
        else:
            return str(obj)

    def encode(self, obj):
        return json.JSONEncoder.encode(self, obj)


class Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        self.json_loaders = kwargs.pop('json_loaders', {})
        json.JSONDecoder.__init__(self, *args, **kwargs)

    def decode(self, s):
        if isinstance(s, basestring):
            for f in self.json_loaders:
                try:
                    v = f(s)
                    return v
                except Exception:
                    continue
        return json.JSONDecoder.decode(self, s)


def dumps(obj, extra_json_dumpers=None):
    json_dumpers_ = dict(json_dumpers)
    json_dumpers_.update(extra_json_dumpers or {})
    obj = convert_keys(obj)
    s = json.dumps(obj, cls=Encoder, separators=(',', ':'), json_dumpers=json_dumpers_)
    return s


def loads(value, extra_json_loaders=()):
    json_loaders_ = json_loaders + list(extra_json_loaders)

    def object_hook(obj):
        for key, value in obj.items():
            if isinstance(value, basestring):
                for f in json_loaders_:
                    try:
                        value = f(value)
                        break
                    except Exception:
                        continue
                obj[key] = value
        return obj
    return json.loads(value, cls=Decoder, json_loaders=json_loaders_, object_hook=object_hook)


def try_loads(s):
    try:
        return loads(s)
    except ValueError:
        return s
