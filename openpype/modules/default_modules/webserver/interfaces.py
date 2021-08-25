from abc import abstractmethod
from openpype.modules import OpenPypeInterface


class IWebServerRoutes(OpenPypeInterface):
    """Other modules interface to register their routes."""
    @abstractmethod
    def webserver_initialization(self, server_manager):
        pass
