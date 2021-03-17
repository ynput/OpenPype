import time
import collections
import threading
from abc import ABCMeta, abstractmethod

import six

from pype.lib import PypeLogger
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

    def start_thread(self):
        if self.idle_thread:
            self.idle_thread.stop()
            self.idle_thread.join()
        self.idle_thread = IdleManagerThread(self)
        self.idle_thread.start()

    def stop_thread(self):
        if self.idle_thread:
            self.idle_thread.stop()
            self.idle_thread.join()

    def on_thread_stop(self):
        self.set_service_failed_icon()


class IdleManagerThread(threading.Thread):
    def __init__(self, module, *args, **kwargs):
        super(IdleManagerThread, self).__init__(*args, **kwargs)
        self.log = PypeLogger().get_logger(self.__class__.__name__)
        self.module = module
        self.threads = []
        self.is_running = False
        self.idle_time = 0

    def stop(self):
        self.is_running = False

    def reset_time(self):
        self.idle_time = 0

    @property
    def time_callbacks(self):
        return self.module.time_callbacks

    def on_stop(self):
        self.is_running = False
        self.log.info("IdleManagerThread has stopped")
        self.module.on_thread_stop()

    def _create_threads(self):
        from .idle_logic import MouseThread, KeyboardThread

        thread_mouse = MouseThread(self.reset_time)
        thread_keyboard = KeyboardThread(self.reset_time)
        return thread_mouse, thread_keyboard

    def run(self):
        self.log.info("IdleManagerThread has started")
        self.is_running = True
        thread_mouse, thread_keyboard = self._create_threads()
        thread_mouse.start()
        thread_keyboard.start()
        try:
            while self.is_running:
                if self.idle_time in self.time_callbacks:
                    for callback in self.time_callbacks[self.idle_time]:
                        thread = threading.Thread(target=callback)
                        thread.start()
                        self.threads.append(thread)

                for thread in tuple(self.threads):
                    if not thread.isAlive():
                        thread.join()
                        self.threads.remove(thread)

                self.idle_time += 1
                time.sleep(1)

        except Exception:
            self.log.warning(
                'Idle Manager service has failed', exc_info=True
            )

        # Threads don't have their attrs when Qt application already finished
        try:
            thread_mouse.stop()
            thread_mouse.join()
        except AttributeError:
            pass

        try:
            thread_keyboard.stop()
            thread_keyboard.join()
        except AttributeError:
            pass

        self.on_stop()
