from functools import partial

from qtpy import QtCore


class RefreshThread(QtCore.QThread):
    refresh_finished = QtCore.Signal(str)

    def __init__(self, thread_id, func, *args, **kwargs):
        super(RefreshThread, self).__init__()
        self._id = thread_id
        self._callback = partial(func, *args, **kwargs)
        self._exception = None
        self._result = None

    @property
    def id(self):
        return self._id

    @property
    def failed(self):
        return self._exception is not None

    def run(self):
        try:
            self._result = self._callback()
        except Exception as exc:
            self._exception = exc
        self.refresh_finished.emit(self.id)

    def get_result(self):
        return self._result
