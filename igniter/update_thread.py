# -*- coding: utf-8 -*-
"""Working thread for update."""
from Qt.QtCore import QThread, Signal, QObject  # noqa

from .bootstrap_repos import (
    BootstrapRepos,
    OpenPypeVersion
)


class UpdateThread(QThread):
    """Install Worker thread.

    This class takes care of finding OpenPype version on user entered path
    (or loading this path from database). If nothing is entered by user,
    OpenPype will create its zip files from repositories that comes with it.

    If path contains plain repositories, they are zipped and installed to
    user data dir.

    """
    progress = Signal(int)
    message = Signal((str, bool))

    def __init__(self, parent=None):
        self._result = None
        self._openpype_version = None
        QThread.__init__(self, parent)

    def set_version(self, openpype_version: OpenPypeVersion):
        self._openpype_version = openpype_version

    def result(self):
        """Result of finished installation."""
        return self._result

    def _set_result(self, value):
        if self._result is not None:
            raise AssertionError("BUG: Result was set more than once!")
        self._result = value

    def run(self):
        """Thread entry point.

        Using :class:`BootstrapRepos` to either install OpenPype as zip files
        or copy them from location specified by user or retrieved from
        database.
        """
        bs = BootstrapRepos(
            progress_callback=self.set_progress, message=self.message)
        version_path = bs.install_version(self._openpype_version)
        self._set_result(version_path)

    def set_progress(self, progress: int) -> None:
        """Helper to set progress bar.

        Args:
            progress (int): Progress in percents.

        """
        self.progress.emit(progress)
