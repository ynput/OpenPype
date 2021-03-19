import time
import threading

from pynput import mouse, keyboard

from pype.lib import PypeLogger


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


class IdleManagerThread(threading.Thread):
    def __init__(self, module, *args, **kwargs):
        super(IdleManagerThread, self).__init__(*args, **kwargs)
        self.log = PypeLogger.get_logger(self.__class__.__name__)
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

    def run(self):
        self.log.info("IdleManagerThread has started")
        self.is_running = True
        thread_mouse = MouseThread(self.reset_time)
        thread_keyboard = KeyboardThread(self.reset_time)
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
