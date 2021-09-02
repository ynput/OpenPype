from abc import abstractmethod
from openpype.modules import OpenPypeInterface


class IFtrackEventHandlerPaths(OpenPypeInterface):
    """Other modules interface to return paths to ftrack event handlers.

    Expected output is dictionary with "server" and "user" keys.
    """
    @abstractmethod
    def get_event_handler_paths(self):
        pass
