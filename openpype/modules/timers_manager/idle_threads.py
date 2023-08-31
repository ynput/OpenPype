import time
import platform
import threading

from openpype.lib import Logger


def get_idle_time():
    return None


if platform.system().lower() == "windows":
    try:
        import win32api

        def _windows_get_idle_time():
            return int((
                win32api.GetTickCount() - win32api.GetLastInputInfo()) / 1000)

        get_idle_time = _windows_get_idle_time

    except BaseException:
        pass


class IdleCallback(object):
    def __init__(self, func, idle_time):
        self._func = func
        self._triggered = False
        self._idle_time = idle_time

    def reset(self):
        self._triggered = False

    def trigger(self, idle_time):
        if self._triggered or idle_time < self._idle_time:
            return

        self._triggered = True
        self._func()


class IdleThreadState(object):
    """Helper to handle state of a thread.

    Python thread may not handle attributes as expected. e.g. having an
    attribute 'stopped' and changing it from different thread may not
    be propagated correctly. Using middle object will cause that code in
    'run' won't look into cache but into the memory pointer.
    """

    def __init__(self):
        self._is_running = False
        self._stopped = False

    def get_is_running(self):
        return self._is_running

    def set_is_running(self, is_running):
        self._is_running = is_running

    def get_stopped(self):
        return self._stopped

    def set_stopped(self, stopped):
        self._stopped = stopped

    is_running = property(get_is_running, set_is_running)
    stopped = property(get_stopped, set_stopped)


class IdleThread(threading.Thread):
    """ Measure user's idle time in seconds.

    Use OS built-in functions to get idle time and trigger a callback when
    needed.
    """

    def __init__(self):
        super(IdleThread, self).__init__()
        self.log = Logger.get_logger(self.__class__.__name__)

        self._idle_time = 0
        self._callbacks = []
        self._reset_callbacks = []
        self._idle_thread_state = IdleThreadState()

    def add_time_callback(self, emit_time, func):
        """ If any module want to use IdleManager, need to use add_time_signal

        Args:
            emit_time (int): Time when signal will be emitted.
            func (Function): Function callback.
        """

        self._callbacks.append(IdleCallback(func, emit_time))

    def add_reset_callback(self, func):
        self._reset_callbacks.append(func)

    @property
    def is_running(self):
        """Thread is running.

        Returns:
            bool: Thread is running.
        """

        return self._idle_thread_state.is_running

    @property
    def idle_time(self):
        return self._idle_time

    def run(self):
        self._idle_thread_state.is_running = True
        self.log.info("IdleManager has started")

        while True:
            print(self._idle_thread_state.stopped)
            if self._idle_thread_state.stopped:
                break

            idle_time = get_idle_time()
            if idle_time is None:
                self._idle_time = None
                break
            self._set_idle_time(idle_time)
            time.sleep(1)

        self._idle_thread_state.is_running = False
        self.log.info("IdleManager has stopped")

    def stop(self):
        """Stop the thread.

        This will cause that the thread should stop in next 0.3 seconds.
        """

        self._idle_thread_state.stopped = True

    def _reset(self, skip_callbacks=False):
        if not skip_callbacks:
            for callback in self._callbacks:
                callback.reset()

        for func in self._reset_callbacks:
            func()

    def _set_idle_time(self, idle_time):
        if self._idle_time == idle_time:
            if idle_time == 0:
                self._reset(skip_callbacks=True)
            return

        previous_idle_time = self._idle_time
        self._idle_time = idle_time
        if previous_idle_time > idle_time:
            self._reset()

        for callback in self._callbacks:
            callback.trigger(idle_time)
