# -*- coding: utf-8 -*-
"""Working thread for installer."""
import os
import sys
from pathlib import Path

from Qt.QtCore import QThread, Signal, QObject  # noqa

from .bootstrap_repos import (
    BootstrapRepos,
    OpenPypeVersionInvalid,
    OpenPypeVersionIOError,
    OpenPypeVersionExists,
    OpenPypeVersion
)

from .tools import validate_mongo_connection


class InstallThread(QThread):
    """Install Worker thread.

    This class takes care of finding OpenPype version on user entered path
    (or loading this path from database). If nothing is entered by user,
    OpenPype will create its zip files from repositories that comes with it.

    If path contains plain repositories, they are zipped and installed to
    user data dir.

    """
    progress = Signal(int)
    message = Signal((str, bool))

    def __init__(self, parent=None,):
        self._mongo = None
        self._path = None
        self._result = None

        QThread.__init__(self, parent)

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
        self.message.emit("Installing OpenPype ...", False)

        # find local version of OpenPype
        bs = BootstrapRepos(
            progress_callback=self.set_progress, message=self.message)
        local_version = OpenPypeVersion.get_installed_version_str()

        # if user did entered nothing, we install OpenPype from local version.
        # zip content of `repos`, copy it to user data dir and append
        # version to it.
        if not self._path:
            # user did not entered url
            if not self._mongo:
                # it not set in environment
                if not os.getenv("OPENPYPE_MONGO"):
                    # try to get it from settings registry
                    try:
                        self._mongo = bs.secure_registry.get_item(
                            "openPypeMongo")
                    except ValueError:
                        self.message.emit(
                            "!!! We need MongoDB URL to proceed.", True)
                        self._set_result(-1)
                        return
                else:
                    self._mongo = os.getenv("OPENPYPE_MONGO")
            else:
                self.message.emit("Saving mongo connection string ...", False)
                bs.secure_registry.set_item("openPypeMongo", self._mongo)

            os.environ["OPENPYPE_MONGO"] = self._mongo

            self.message.emit(
                f"Detecting installed OpenPype versions in {bs.data_dir}",
                False)
            detected = bs.find_openpype(include_zips=True)

            if detected:
                if OpenPypeVersion(
                        version=local_version, path=Path()) < detected[-1]:
                    self.message.emit((
                        f"Latest installed version {detected[-1]} is newer "
                        f"then currently running {local_version}"
                    ), False)
                    self.message.emit("Skipping OpenPype install ...", False)
                    if detected[-1].path.suffix.lower() == ".zip":
                        bs.extract_openpype(detected[-1])
                    self._set_result(0)
                    return

                if OpenPypeVersion(version=local_version).get_main_version() == detected[-1].get_main_version():  # noqa
                    self.message.emit((
                        f"Latest installed version is the same as "
                        f"currently running {local_version}"
                    ), False)
                    self.message.emit("Skipping OpenPype install ...", False)
                    self._set_result(0)
                    return

                self.message.emit((
                    "All installed versions are older then "
                    f"currently running one {local_version}"
                ), False)
            else:
                if getattr(sys, 'frozen', False):
                    self.message.emit("None detected.", True)
                    self.message.emit(("We will use OpenPype coming with "
                                       "installer."), False)
                    openpype_version = bs.create_version_from_frozen_code()
                    if not openpype_version:
                        self.message.emit(
                            f"!!! Install failed - {openpype_version}", True)
                        self._set_result(-1)
                        return
                    self.message.emit(f"Using: {openpype_version}", False)
                    bs.install_version(openpype_version)
                    self.message.emit(f"Installed as {openpype_version}", False)
                    self.progress.emit(100)
                    self._set_result(1)
                    return
                else:
                    self.message.emit("None detected.", False)

            self.message.emit(
                f"We will use local OpenPype version {local_version}", False)

            local_openpype = bs.create_version_from_live_code()
            if not local_openpype:
                self.message.emit(
                    f"!!! Install failed - {local_openpype}", True)
                self._set_result(-1)
                return

            try:
                bs.install_version(local_openpype)
            except (OpenPypeVersionExists,
                    OpenPypeVersionInvalid,
                    OpenPypeVersionIOError) as e:
                self.message.emit(f"Installed failed: ", True)
                self.message.emit(str(e), True)
                self._set_result(-1)
                return

            self.message.emit(f"Installed as {local_openpype}", False)
            self.progress.emit(100)
            self._set_result(1)
            return
        else:
            # if we have mongo connection string, validate it, set it to
            # user settings and get OPENPYPE_PATH from there.
            if self._mongo:
                if not validate_mongo_connection(self._mongo):
                    self.message.emit(
                        f"!!! invalid mongo url {self._mongo}", True)
                    self._set_result(-1)
                    return
                bs.secure_registry.set_item("openPypeMongo", self._mongo)
                os.environ["OPENPYPE_MONGO"] = self._mongo

            self.message.emit(f"processing {self._path}", True)
            repo_file = bs.process_entered_location(self._path)

            if not repo_file:
                self.message.emit("!!! Cannot install", True)
                self._set_result(-1)
                return

        self.progress.emit(100)
        self._set_result(1)
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
