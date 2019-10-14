from .rest_api import RestApiServer
from .base_class import RestApi, abort, route, register_statics
from .lib import (
    RestMethods,
    UrlData,
    RequestData,
    Query,
    Fragment,
    Params,
    Handler,
    CallbackResult
)


def tray_init(tray_widget, main_widget):
    return RestApiServer()
