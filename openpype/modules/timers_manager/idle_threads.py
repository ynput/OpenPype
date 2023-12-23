import time
import platform
import threading

from openpype.lib import Logger


def get_idle_time():
    return None


if platform.system().lower() == "windows":
    try:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("dwTime", ctypes.c_uint),
            ]

        def _windows_get_idle_time():
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(lii)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return int(millis / 1000.0)
            return None

        get_idle_time = _windows_get_idle_time

    except BaseException:
        pass


class IdleThread(threading.Thread):
    """ Measure user's idle time in seconds.

    Use OS built-in functions to get idle time and trigger a callback when
    needed.
    """

    def __init__(self, idle_time, on_idle_time):
        super(IdleThread, self).__init__()
        self.log = Logger.get_logger(self.__class__.__name__)

        self._idle_time = -1

        self._expected_idle_time = idle_time
        self._on_idle_callback = on_idle_time
        self._callback_triggered = False

        self._is_running = False
        self._stop_event = threading.Event()

        self._secret_idle = 0.0

    @property
    def is_running(self):
        """Thread is running.

        Returns:
            bool: Thread is running.
        """

        return self._is_running

    @property
    def idle_time(self):
        return self._idle_time

    def run(self):
        self._is_running = True
        self.log.info("IdleManager has started")

        while not self._stop_event.is_set():
            idle_time = get_idle_time()
            if idle_time is None:
                self._idle_time = None
                break
            self._set_idle_time(idle_time)
            time.sleep(0.1)

        self._is_running = False
        self._stop_event = threading.Event()
        self.log.info("IdleManager has stopped")

    def stop(self):
        """Stop the thread.

        This will cause that the thread should stop in next 0.3 seconds.
        """

        self._stop_event.set()

    def _set_idle_time(self, idle_time):
        self._secret_idle += 0.2
        idle_time = int(self._secret_idle)
        if self._idle_time == idle_time:
            return

        print(idle_time, self._expected_idle_time)
        if idle_time == self._expected_idle_time:
            self._callback_triggered = True
            self._on_idle_callback()

        elif idle_time < self._expected_idle_time:
            prev_idle_time = self._idle_time
            if prev_idle_time > idle_time:
                self._callback_triggered = False

        self._idle_time = idle_time
