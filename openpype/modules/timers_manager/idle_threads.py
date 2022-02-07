import time
from Qt import QtCore
from pynput import mouse, keyboard

from openpype.lib import PypeLogger


class IdleItem:
    """Python object holds information if state of idle changed.

    This item is used to be independent from Qt objects.
    """
    def __init__(self):
        self.changed = False

    def reset(self):
        self.changed = False

    def set_changed(self, changed=True):
        self.changed = changed


class IdleManager(QtCore.QThread):
    """ Measure user's idle time in seconds.
    Idle time resets on keyboard/mouse input.
    Is able to emit signals at specific time idle.
    """
    time_signals = {}
    idle_time = 0
    signal_reset_timer = QtCore.Signal()

    def __init__(self):
        super(IdleManager, self).__init__()
        self.log = PypeLogger.get_logger(self.__class__.__name__)
        self.signal_reset_timer.connect(self._reset_time)

        self.idle_item = IdleItem()

        self._is_running = False
        self._mouse_thread = None
        self._keyboard_thread = None

    def add_time_signal(self, emit_time, signal):
        """ If any module want to use IdleManager, need to use add_time_signal

        Args:
            emit_time(int): Time when signal will be emitted.
            signal(QtCore.Signal): Signal that will be emitted
                (without objects).
        """
        if emit_time not in self.time_signals:
            self.time_signals[emit_time] = []
        self.time_signals[emit_time].append(signal)

    @property
    def is_running(self):
        return self._is_running

    def _reset_time(self):
        self.idle_time = 0

    def stop(self):
        self._is_running = False

    def _on_mouse_destroy(self):
        self._mouse_thread = None

    def _on_keyboard_destroy(self):
        self._keyboard_thread = None

    def run(self):
        self.log.info('IdleManager has started')
        self._is_running = True

        thread_mouse = MouseThread(self.idle_item)
        thread_keyboard = KeyboardThread(self.idle_item)

        thread_mouse.destroyed.connect(self._on_mouse_destroy)
        thread_keyboard.destroyed.connect(self._on_keyboard_destroy)

        self._mouse_thread = thread_mouse
        self._keyboard_thread = thread_keyboard

        thread_mouse.start()
        thread_keyboard.start()

        # Main loop here is each second checked if idle item changed state
        while self._is_running:
            if self.idle_item.changed:
                self.idle_item.reset()
                self.signal_reset_timer.emit()
            else:
                self.idle_time += 1

            if self.idle_time in self.time_signals:
                for signal in self.time_signals[self.idle_time]:
                    signal.emit()
            time.sleep(1)

        self._post_run()
        self.log.info('IdleManager has stopped')

    def _post_run(self):
        # Stop threads if still exist
        if self._mouse_thread is not None:
            self._mouse_thread.signal_stop.emit()
            self._mouse_thread.terminate()
            self._mouse_thread.wait()

        if self._keyboard_thread is not None:
            self._keyboard_thread.signal_stop.emit()
            self._keyboard_thread.terminate()
            self._keyboard_thread.wait()


class MouseThread(QtCore.QThread):
    """Listens user's mouse movement."""
    signal_stop = QtCore.Signal()

    def __init__(self, idle_item):
        super(MouseThread, self).__init__()
        self.signal_stop.connect(self.stop)
        self.m_listener = None
        self.idle_item = idle_item

    def stop(self):
        if self.m_listener is not None:
            self.m_listener.stop()

    def on_move(self, *args, **kwargs):
        self.idle_item.set_changed()

    def run(self):
        self.m_listener = mouse.Listener(on_move=self.on_move)
        self.m_listener.start()


class KeyboardThread(QtCore.QThread):
    """Listens user's keyboard input
    """
    signal_stop = QtCore.Signal()

    def __init__(self, idle_item):
        super(KeyboardThread, self).__init__()
        self.signal_stop.connect(self.stop)
        self.k_listener = None
        self.idle_item = idle_item

    def stop(self):
        if self.k_listener is not None:
            listener = self.k_listener
            self.k_listener = None
            listener.stop()

    def on_press(self, *args, **kwargs):
        self.idle_item.set_changed()

    def run(self):
        self.k_listener = keyboard.Listener(on_press=self.on_press)
        self.k_listener.start()
