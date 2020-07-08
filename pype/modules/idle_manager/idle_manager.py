import time
import collections
import threading
from pynput import mouse, keyboard
from pype.api import Logger


class IdleManager(threading.Thread):
    """ Measure user's idle time in seconds.
    Idle time resets on keyboard/mouse input.
    Is able to emit signals at specific time idle.
    """
    time_callbacks = collections.defaultdict(list)
    idle_time = 0

    def __init__(self):
        super(IdleManager, self).__init__()
        self.log = Logger().get_logger(self.__class__.__name__)
        self.qaction = None
        self.failed_icon = None
        self._is_running = False
        self.threads = []

    def set_qaction(self, qaction, failed_icon):
        self.qaction = qaction
        self.failed_icon = failed_icon

    def tray_start(self):
        self.start()

    def tray_exit(self):
        self.stop()
        try:
            self.time_callbacks = {}
        except Exception:
            pass

    def add_time_callback(self, emit_time, callback):
        """If any module want to use IdleManager, need to use this method.

        Args:
            emit_time(int): Time when callback will be triggered.
            callback(func): Callback that will be triggered.
        """
        self.time_callbacks[emit_time].append(callback)

    @property
    def is_running(self):
        return self._is_running

    def _reset_time(self):
        self.idle_time = 0

    def stop(self):
        self._is_running = False

    def run(self):
        self.log.info('IdleManager has started')
        self._is_running = True
        thread_mouse = MouseThread(self._reset_time)
        thread_mouse.start()
        thread_keyboard = KeyboardThread(self._reset_time)
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

        if self.qaction and self.failed_icon:
            self.qaction.setIcon(self.failed_icon)

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

        self._is_running = False
        self.log.info('IdleManager has stopped')


class MouseThread(mouse.Listener):
    """Listens user's mouse movement."""

    def __init__(self, callback):
        super(MouseThread, self).__init__(on_move=self.on_move)
        self.callback = callback

    def on_move(self, posx, posy):
        self.callback()


class KeyboardThread(keyboard.Listener):
    """Listens user's keyboard input."""

    def __init__(self, callback):
        super(KeyboardThread, self).__init__(on_press=self.on_press)

        self.callback = callback

    def on_press(self, key):
        self.callback()
