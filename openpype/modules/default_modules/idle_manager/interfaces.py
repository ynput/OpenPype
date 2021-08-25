from abc import abstractmethod
from openpype.modules import OpenPypeInterface


class IIdleManager(OpenPypeInterface):
    """Other modules interface to return callbacks by idle time in seconds.

    Expected output is dictionary with seconds <int> as keys and callback/s
    as value, value may be callback of list of callbacks.
    EXAMPLE:
    ```
    {
        60: self.on_minute_idle
    }
    ```
    """
    idle_manager = None

    @abstractmethod
    def callbacks_by_idle_time(self):
        pass

    @property
    def idle_time(self):
        if self.idle_manager:
            return self.idle_manager.idle_time
