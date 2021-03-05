# -*- coding: utf-8 -*-
"""Working thread for installer."""
import os
import sys
from pathlib import Path

from Qt.QtCore import QThread, Signal, QObject  # noqa

from .bootstrap_repos import (
    BootstrapRepos,
    PypeVersionInvalid,
    PypeVersionIOError,
    PypeVersionExists,
    PypeVersion
)

from .tools import validate_mongo_connection


class InstallResult(QObject):
    """Used to pass results back."""
    def __init__(self, value):
        self.status = value


class InstallThread(QThread):
    """Install Worker thread.

    This class takes care of finding Pype version on user entered path
    (or loading this path from database). If nothing is entered by user,
    Pype will create its zip files from repositories that comes with it.

    If path contains plain repositories, they are zipped and installed to
    user data dir.

    """
    progress = Signal(int)
    message = Signal((str, bool))
    finished = Signal(object)

    def __init__(self, callback, parent=None,):
        self._mongo = None
        self._path = None
        self.result_callback = callback

        QThread.__init__(self, parent)
        self.finished.connect(callback)

    def run(self):
        """Thread entry point.

        Using :class:`BootstrapRepos` to either install Pype as zip files
        or copy them from location specified by user or retrieved from
        database.

        """
        self.message.emit("Installing Pype ...", False)

        # find local version of Pype
        bs = BootstrapRepos(
            progress_callback=self.set_progress, message=self.message)
        local_version = bs.get_local_live_version()

        # if user did entered nothing, we install Pype from local version.
        # zip content of `repos`, copy it to user data dir and append
        # version to it.
        if not self._path:
            # user did not entered url
            if not self._mongo:
                # it not set in environment
                if not os.getenv("PYPE_MONGO"):
                    # try to get it from settings registry
                    try:
                        self._mongo = bs.registry.get_secure_item("pypeMongo")
                    except ValueError:
                        self.message.emit(
                            "!!! We need MongoDB URL to proceed.", True)
                        self.finished.emit(InstallResult(-1))
                        return
                else:
                    self._mongo = os.getenv("PYPE_MONGO")
            else:
                bs.registry.set_secure_item("pypeMongo", self._mongo)

            os.environ["PYPE_MONGO"] = self._mongo

            self.message.emit(
                f"Detecting installed Pype versions in {bs.data_dir}", False)
            detected = bs.find_pype(include_zips=True)

            if detected:
                if PypeVersion(
                        version=local_version, path=Path()) < detected[-1]:
                    self.message.emit((
                        f"Latest installed version {detected[-1]} is newer "
                        f"then currently running {local_version}"
                    ), False)
                    self.message.emit("Skipping Pype install ...", False)
                    if detected[-1].path.suffix.lower() == ".zip":
                        bs.extract_pype(detected[-1])
                    self.finished.emit(InstallResult(0))

                if PypeVersion(version=local_version).get_main_version() == detected[-1].get_main_version():  # noqa
                    self.message.emit((
                        f"Latest installed version is the same as "
                        f"currently running {local_version}"
                    ), False)
                    self.message.emit("Skipping Pype install ...", False)
                    self.finished.emit(InstallResult(0))

                self.message.emit((
                    "All installed versions are older then "
                    f"currently running one {local_version}"
                ), False)
            else:
                if getattr(sys, 'frozen', False):
                    self.message.emit("None detected.", True)
                    self.message.emit(("We will use Pype coming with "
                                       "installer."), False)
                    pype_version = bs.create_version_from_frozen_code()
                    if not pype_version:
                        self.message.emit(
                            f"!!! Install failed - {pype_version}", True)
                        self.finished.emit(InstallResult(-1))
                    self.message.emit(f"Using: {pype_version}", False)
                    bs.install_version(pype_version)
                    self.message.emit(f"Installed as {pype_version}", False)
                    self.finished.emit(InstallResult(1))
                else:
                    self.message.emit("None detected.", False)

            self.message.emit(
                f"We will use local Pype version {local_version}", False)

            local_pype = bs.create_version_from_live_code()
            if not local_pype:
                self.message.emit(
                    f"!!! Install failed - {local_pype}", True)
                self.finished.emit(InstallResult(-1))

            try:
                bs.install_version(local_pype)
            except (PypeVersionExists,
                    PypeVersionInvalid,
                    PypeVersionIOError) as e:
                self.message.emit(f"Installed failed", True)
                self.finished.emit(InstallResult(-1))

            self.message.emit(f"Installed as {local_pype}", False)
        else:
            # if we have mongo connection string, validate it, set it to
            # user settings and get PYPE_PATH from there.
            if self._mongo:
                if not validate_mongo_connection(self._mongo):
                    self.message.emit(
                        f"!!! invalid mongo url {self._mongo}", True)
                    self.finished.emit(InstallResult(-1))
                bs.registry.set_secure_item("pypeMongo", self._mongo)
                os.environ["PYPE_MONGO"] = self._mongo

            self.message.emit(f"processing {self._path}", True)
            repo_file = bs.process_entered_location(self._path)

            if not repo_file:
                self.message.emit("!!! Cannot install", True)
                self.finished.emit(InstallResult(-1))
                return

        self.finished.emit(InstallResult(1))
        return

    def set_path(self, path: str) -> None:
        """Helper to set path.

        Args:
            path (str): Path to set.

        """
        self._path = path

    def set_mongo(self, mongo: str) -> None:
        """Helper to set mongo url.

        Args:
            mongo (str): Mongodb url.

        """
        self._mongo = mongo

    def set_progress(self, progress: int) -> None:
        """Helper to set progress bar.

        Args:
            progress (int): Progress in percents.

        """
        self.progress.emit(progress)
