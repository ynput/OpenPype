from .rest_api import RestApiServer


def tray_init(tray_widget, main_widget):
    return RestApiServer()
