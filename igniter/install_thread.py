# -*- coding: utf-8 -*-
"""Working thread for installer."""
import os
from Qt.QtCore import QThread, Signal
from igniter.tools import load_environments

from .bootstrap_repos import BootstrapRepos
from .tools import validate_mongo_connection


class InstallThread(QThread):
    """Install Worker thread.

    This class takes care of finding Pype version on user entered path
    (or loading this path from database). If nothing is entered by user,
    Pype will create its zip files from repositories that comes with it.

    If path contains plain repositories, they are zipped and installed to
    user data dir.

    Attributes:
        progress (Signal): signal reporting progress back o UI.
        message (Signal): message displaying in UI console.

    """

    progress = Signal(int)
    message = Signal((str, bool))

    def __init__(self, parent=None):
        self._mongo = None
        self._path = None
        QThread.__init__(self, parent)

    def run(self):
        self.message.emit("Installing Pype ...", False)
        # find local version of Pype
        bs = BootstrapRepos(progress_callback=self.set_progress)
        local_version = bs.get_local_version()

        # if user did entered nothing, we install Pype from local version.
        # zip content of `repos`, copy it to user data dir and append
        # version to it.
        if not self._path:
            self.ask_for_mongo.emit(True)
            self.message.emit(
                f"We will use local Pype version {local_version}", False)
            repo_file = bs.install_live_repos()
            if not repo_file:
                self.message.emit(
                    f"!!! install failed - {repo_file}", True)
                return
            self.message.emit(f"installed as {repo_file}", False)
        else:
            if self._mongo:
                if not validate_mongo_connection(self._mongo):
                    self.message.emit(
                        f"!!! invalid mongo url {self._mongo}", True)
                    return
                bs.registry.set_secure_item("avalonMongo", self._mongo)
                os.environ["AVALON_MONGO"] = self._mongo

            repo_file = bs.process_entered_location(self._path)

            if not repo_file:
                self.message.emit(f"!!! Cannot install", True)
                return

    def set_path(self, path: str) -> None:
        self._path = path

    def set_mongo(self, mongo: str) -> None:
        self._mongo = mongo

    def set_progress(self, progress: int):
        self.progress.emit(progress)
