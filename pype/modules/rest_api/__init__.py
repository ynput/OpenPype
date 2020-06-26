from .rest_api import RestApiServer
from .base_class import RestApi, abort, route, register_statics
from .lib import RestMethods, CallbackResult

CLASS_DEFINIION = RestApiServer


def tray_init(tray_widget, main_widget):
    return RestApiServer()
