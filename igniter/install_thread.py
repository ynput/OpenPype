# -*- coding: utf-8 -*-
"""Working thread for installer."""
import sys
import os
from Qt.QtCore import QThread, Signal
from pype import settings
from igniter.tools import load_environments

from .bootstrap_repos import BootstrapRepos


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

    def __init__(self, parent=None):
        self.progress = Signal(int)
        self.message = Signal((str, bool))
        self._path = None
        QThread.__init__(self, parent)

    def run(self):
        self.message.emit("Installing Pype ...", False)
        # find local version of Pype
        bs = BootstrapRepos()
        local_version = bs.get_local_version()

        # if user did entered nothing, we install Pype from local version.
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
        else:
            pype_path = None
            # find central pype location from database
            if self._path.startswith("mongodb"):
                self.message.emit("determining Pype location from db...")
                os.environ["AVALON_MONGO"] = self._path
                env = load_environments()
                if not env.get("PYPE_ROOT"):
                    self.message.emit(
                        "!!! cannot load path to Pype from db", True)
                    return

                self.message.emit(f"path loaded from database ...", False)
                self.message.emit(env.get("PYPE_ROOT"), False)
                if not os.path.exists(env.get("PYPE_ROOT")):
                    self.message.emit(f"!!! path doesn't exist", True)
                    return
                pype_path = env.get("PYPE_ROOT")
            if not pype_path:
                pype_path = self._path

            if not os.path.exists(pype_path):
                self.message.emit(f"!!! path doesn't exist", True)
                return

            # detect Pype in path







    def set_path(self, path: str) -> None:
        self._path = path

    def set_progress(self, progress: int):
        self.progress.emit(progress)
