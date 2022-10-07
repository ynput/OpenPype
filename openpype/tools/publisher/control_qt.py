import collections

from Qt import QtCore

from .control import MainThreadItem, PublisherController


class MainThreadProcess(QtCore.QObject):
    """Qt based main thread process executor.

    Has timer which controls each 50ms if there is new item to process.

    This approach gives ability to update UI meanwhile plugin is in progress.
    """

    count_timeout = 2

    def __init__(self):
        super(MainThreadProcess, self).__init__()
        self._items_to_process = collections.deque()

        timer = QtCore.QTimer()
        timer.setInterval(0)

        timer.timeout.connect(self._execute)

        self._timer = timer
        self._switch_counter = self.count_timeout

    def process(self, func, *args, **kwargs):
        item = MainThreadItem(func, *args, **kwargs)
        self.add_item(item)

    def add_item(self, item):
        self._items_to_process.append(item)

    def _execute(self):
        if not self._items_to_process:
            return

        if self._switch_counter > 0:
            self._switch_counter -= 1
            return

        self._switch_counter = self.count_timeout

        item = self._items_to_process.popleft()
        item.process()

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    def clear(self):
        if self._timer.isActive():
            self._timer.stop()
        self._items_to_process = collections.deque()


class QtPublisherController(PublisherController):
    def __init__(self, *args, **kwargs):
        self._main_thread_processor = MainThreadProcess()

        super(QtPublisherController, self).__init__(*args, **kwargs)

        self.event_system.add_callback(
            "publish.process.started", self._qt_on_publish_start
        )
        self.event_system.add_callback(
            "publish.process.stopped", self._qt_on_publish_stop
        )

    def _reset_publish(self):
        super(QtPublisherController, self)._reset_publish()
        self._main_thread_processor.clear()

    def _process_main_thread_item(self, item):
        self._main_thread_processor.add_item(item)

    def _qt_on_publish_start(self):
        self._main_thread_processor.start()

    def _qt_on_publish_stop(self):
        self._main_thread_processor.stop()
