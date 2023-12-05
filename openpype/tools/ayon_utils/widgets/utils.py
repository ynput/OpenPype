import os
from functools import partial

from qtpy import QtCore, QtGui

from openpype.tools.utils.lib import get_qta_icon_by_name_and_color


class RefreshThread(QtCore.QThread):
    refresh_finished = QtCore.Signal(str)

    def __init__(self, thread_id, func, *args, **kwargs):
        super(RefreshThread, self).__init__()
        self._id = thread_id
        self._callback = partial(func, *args, **kwargs)
        self._exception = None
        self._result = None
        self.finished.connect(self._on_finish_callback)

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

    def get_result(self):
        return self._result

    def _on_finish_callback(self):
        """Trigger custom signal with thread id.

        Listening for 'finished' signal we make sure that execution of thread
            finished and QThread object can be safely deleted.
        """

        self.refresh_finished.emit(self.id)


class _IconsCache:
    """Cache for icons."""

    _cache = {}
    _default = None

    @classmethod
    def _get_cache_key(cls, icon_def):
        parts = []
        icon_type = icon_def["type"]
        if icon_type == "path":
            parts = [icon_type, icon_def["path"]]

        elif icon_type == "awesome-font":
            parts = [icon_type, icon_def["name"], icon_def["color"]]
        return "|".join(parts)

    @classmethod
    def get_icon(cls, icon_def):
        if not icon_def:
            return None
        icon_type = icon_def["type"]
        cache_key = cls._get_cache_key(icon_def)
        cache = cls._cache.get(cache_key)
        if cache is not None:
            return cache

        icon = None
        if icon_type == "path":
            path = icon_def["path"]
            if os.path.exists(path):
                icon = QtGui.QIcon(path)

        elif icon_type == "awesome-font":
            icon_name = icon_def["name"]
            icon_color = icon_def["color"]
            icon = get_qta_icon_by_name_and_color(icon_name, icon_color)
            if icon is None:
                icon = get_qta_icon_by_name_and_color(
                    "fa.{}".format(icon_name), icon_color)
        if icon is None:
            icon = cls.get_default()
        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def get_default(cls):
        pix = QtGui.QPixmap(1, 1)
        pix.fill(QtCore.Qt.transparent)
        return QtGui.QIcon(pix)


def get_qt_icon(icon_def):
    """Returns icon from cache or creates new one.

    Args:
        icon_def (dict[str, Any]): Icon definition.

    Returns:
        QtGui.QIcon: Icon.
    """

    return _IconsCache.get_icon(icon_def)
