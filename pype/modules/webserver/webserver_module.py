from .. import PypeModule, ITrayService


class WebServerModule(PypeModule, ITrayService):
    name = "Websocket server"
    label = "WebServer"

    def initialize(self, module_settings):
        self.enabled = True
        self.server_manager = None

        # TODO find free port
        self.port = 8098

    def connect_with_modules(self, *_a, **_kw):
        return

    def tray_init(self):
        self.create_server_manager()

    def tray_start(self):
        self.start_server()

    def tray_exit(self):
        self.stop_server()

    def start_server(self):
        if self.server_manager:
            self.server_manager.start_server()

    def stop_server(self):
        if self.server_manager:
            self.server_manager.stop_server()

    def create_server_manager(self):
        if self.server_manager:
            return

        from .server import WebServerManager

        self.server_manager = WebServerManager(self)
        self.server_manager.on_stop_callbacks.append(
            self.set_service_failed_icon
        )
