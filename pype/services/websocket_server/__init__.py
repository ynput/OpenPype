from .module import WebSocketModule
from .server import Namespace


def tray_init(tray_widget, main_widget):
    return WebSocketModule()


__all__ = [
    "WebSocketModule",
    "Namespace",
    "tray_init"
]
