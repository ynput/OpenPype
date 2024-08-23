# -*- coding: utf-8 -*-
"""Working thread for update."""
import os
import re
import platform
import subprocess

from pathlib import Path

from qtpy import QtCore

from .bootstrap_repos import (
    BootstrapRepos,
    OpenPypeVersion
)


class UpdateThread(QtCore.QThread):
    """Install Worker thread.

    This class takes care of finding OpenPype version on user entered path
    (or loading this path from database). If nothing is entered by user,
    OpenPype will create its zip files from repositories that comes with it.

    If path contains plain repositories, they are zipped and installed to
    user data dir.

    """
    progress_signal = QtCore.Signal(int)
    log_signal = QtCore.Signal((str, bool))
    step_text_signal = QtCore.Signal(str)

    def __init__(self, parent=None):
        self._result = None
        self._openpype_version = None
        super().__init__(parent)

    def set_version(self, openpype_version: OpenPypeVersion):
        self._openpype_version = openpype_version

    def result(self):
        """Result of finished installation."""
        return self._result

    def _set_result(self, value):
        if self._result is not None:
            raise AssertionError("BUG: Result was set more than once!")
        self._result = value

    def _extract_zxp_info_from_manifest(self, version_path, host):
        path_manifest = version_path.joinpath("openpype", "hosts", host, "api", "extension", "CSXS", "manifest.xml")
        pattern_regex_extension_id = r"ExtensionBundleId=\"(?P<extension_id>[\w.]+)\""
        pattern_regex_extension_version = r"ExtensionBundleVersion=\"(?P<extension_version>[\d.]+)\""

        extension_id = ""
        extension_version = ""
        try:
            with open(path_manifest, mode="r") as f:
                content = f.read()
                match_extension_id = re.search(pattern_regex_extension_id, content)
                match_extension_version = re.search(pattern_regex_extension_version, content)
                if match_extension_id:
                    extension_id = match_extension_id.group("extension_id")
                if match_extension_version:
                    extension_version = match_extension_version.group("extension_version")
        except IOError as e:
            self.log_signal.emit("I/O error({}): {}".format(e.errno, e.strerror), True)
        except Exception as e:  # handle other exceptions such as attribute errors
            self.log_signal.emit("Unexpected error: {}".format(e), True)

        return extension_id, extension_version

    def _update_zxp_extensions(self, version_path):
        if not version_path:
            return

        # Check the current OS
        low_platform = platform.system().lower()
        if low_platform == "linux":
            # Adobe software isn't available on Linux
            return

        path_prog_folder = Path(os.environ["OPENPYPE_ROOT"]).resolve().joinpath("vendor", "bin", "ex_man_cmd")
        if low_platform == "windows":
            path_prog = path_prog_folder.joinpath("windows", "ExManCmd.exe")
        else:
            path_prog = path_prog_folder.joinpath("macos", "MacOS", "ExManCmd")

        hosts = ["aftereffects", "photoshop"]
        for host in hosts:
            extension_id, extension_version = self._extract_zxp_info_from_manifest(version_path, host)

            if not extension_id or not extension_version:
                # ZXP extension seems invalid, skipping
                continue

            # Remove installed ZXP extension
            self.step_text_signal.emit("Removing installed ZXP extension for <b>{}</b> ...".format(host))
            subprocess.run([str(path_prog), "/remove", extension_id])

            # Install ZXP shipped in the current version folder
            fullpath_curr_zxp_extension = version_path.joinpath("openpype", "hosts", host, "api", "extension.zxp")
            if not fullpath_curr_zxp_extension.exists():
                self.log_signal.emit("Cannot find ZXP extension for {}, looked at: {}".format(
                    host, str(fullpath_curr_zxp_extension)), True)
                continue

            self.step_text_signal.emit("Install ZXP extension for <b>{}</b> ...".format(host))
            completed_process = subprocess.run([str(path_prog), "/install", str(fullpath_curr_zxp_extension)],
                                               capture_output=True)
            if completed_process.returncode != 0 or completed_process.stderr:
                self.log_signal.emit("Couldn't install the ZXP extension for {} "
                                     "due to an error: full log: {}\n{}".format(host,
                                                                                completed_process.stdout,
                                                                                completed_process.stderr), True)

    def run(self):
        """Thread entry point.

        Using :class:`BootstrapRepos` to either install OpenPype as zip files
        or copy them from location specified by user or retrieved from
        database.
        """
        bs = BootstrapRepos(
            progress_callback=self.set_progress, log_signal=self.log_signal)

        bs.set_data_dir(OpenPypeVersion.get_local_openpype_path())
        version_path = bs.install_version(self._openpype_version)
        self._update_zxp_extensions(version_path)
        self._set_result(version_path)

    def set_progress(self, progress: int) -> None:
        """Helper to set progress bar.

        Args:
            progress (int): Progress in percents.

        """
        self.progress_signal.emit(progress)
