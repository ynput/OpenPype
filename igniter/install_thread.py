# -*- coding: utf-8 -*-
"""Working thread for installer."""
import sys
from Qt.QtCore import QThread, Signal

from .bootstrap_repos import BootstrapRepos


class InstallThread(QThread):

    progress = Signal(int)
    message = Signal((str, bool))
    _path = None

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

    def run(self):
        self.message.emit("Installing Pype ...", False)
        bs = BootstrapRepos()
        local_version = bs.get_local_version()

        if getattr(sys, "freeze", None):
            # copy frozen repo zip
            pass
        else:
            # we are running from live code.
            # zip content of `repos`, copy it to user data dir and append
            # version to it.
            if not self._path:
                self.message.emit(
                    f"We will use local Pype version {local_version}", False)
                repo_file = bs.install_live_repos(
                    progress_callback=self.set_progress)
                if not repo_file:
                    self.message.emit(
                        f"!!! install failed - {repo_file}", True)
                    return
                self.message.emit(f"installed as {repo_file}", False)

    def set_path(self, path: str) -> None:
        self._path = path

    def set_progress(self, progress: int):
        self.progress.emit(progress)
