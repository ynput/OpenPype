import collections
from abc import ABCMeta, abstractmethod

import six

from pype.modules import PypeModule, ITrayService


@six.add_metaclass(ABCMeta)
class IIdleManager:
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


class IdleManager(PypeModule, ITrayService):
    """ Measure user's idle time in seconds.
    Idle time resets on keyboard/mouse input.
    Is able to emit signals at specific time idle.
    """
    label = "Idle Service"
    name = "idle_manager"

    def initialize(self, module_settings):
        idle_man_settings = module_settings[self.name]
        self.enabled = idle_man_settings["enabled"]

        self.time_callbacks = collections.defaultdict(list)
        self.idle_thread = None

    def tray_init(self):
        return

    def tray_start(self):
        self.start_thread()

    def tray_exit(self):
        self.stop_thread()
        try:
            self.time_callbacks = {}
        except Exception:
            pass

    def connect_with_modules(self, enabled_modules):
        for module in enabled_modules:
            if not isinstance(module, IIdleManager):
                continue

            module.idle_manager = self
            callbacks_items = module.callbacks_by_idle_time() or {}
            for emit_time, callbacks in callbacks_items.items():
                if not isinstance(callbacks, (tuple, list, set)):
                    callbacks = [callbacks]
                self.time_callbacks[emit_time].extend(callbacks)

    @property
    def idle_time(self):
        if self.idle_thread and self.idle_thread.is_running:
            return self.idle_thread.idle_time

    def _create_thread(self):
        from .idle_threads import IdleManagerThread

        return IdleManagerThread(self)

    def start_thread(self):
        if self.idle_thread:
            self.idle_thread.stop()
            self.idle_thread.join()
        self.idle_thread = self._create_thread()
        self.idle_thread.start()

    def stop_thread(self):
        if self.idle_thread:
            self.idle_thread.stop()
            self.idle_thread.join()

    def on_thread_stop(self):
        self.set_service_failed_icon()
