from .websocket_server import WebSocketServer


def tray_init(tray_widget, main_widget):
    return WebSocketServer()
