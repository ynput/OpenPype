from abc import abstractmethod
from openpype.modules import OpenPypeInterface


class ITimersManager(OpenPypeInterface):
    timer_manager_module = None

    @abstractmethod
    def stop_timer(self):
        pass

    @abstractmethod
    def start_timer(self, data):
        pass

    def timer_started(self, data):
        if not self.timer_manager_module:
            return

        self.timer_manager_module.timer_started(self.id, data)

    def timer_stopped(self):
        if not self.timer_manager_module:
            return

        self.timer_manager_module.timer_stopped(self.id)
