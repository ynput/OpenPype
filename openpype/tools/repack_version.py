# -*- coding: utf-8 -*-
"""Script to rehash and repack current version."""

import enlighten
import blessed
from pathlib import Path
import platform
from zipfile import ZipFile
from typing import List
import hashlib
import sys
from igniter.bootstrap_repos import OpenPypeVersion


class VersionRepacker:

    def __init__(self, directory: str):
        self._term = blessed.Terminal()
        self._manager = enlighten.get_manager()
        self._last_increment = 0
        self.version_path = Path(directory)
        self.zip_path = self.version_path.parent
        _version = {}
        with open(self.version_path / "openpype" / "version.py") as fp:
            exec(fp.read(), _version)
        self._version_py = _version["__version__"]
        del _version

    def _print(self, msg: str, message_type: int = 0) -> None:
        """Print message to console.

        Args:
            msg (str): message to print
            message_type (int): type of message (0 info, 1 error, 2 note)

        """
        if message_type == 0:
            header = self._term.aquamarine3(">>> ")
        elif message_type == 1:
            header = self._term.orangered2("!!! ")
        elif message_type == 2:
            header = self._term.tan1("... ")
        else:
            header = self._term.darkolivegreen3("--- ")

        print("{}{}".format(header, msg))

    @staticmethod
    def sha256sum(filename):
        """Calculate sha256 for content of the file.

        Args:
             filename (str): Path to file.

        Returns:
            str: hex encoded sha256

        """
        h = hashlib.sha256()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(filename, 'rb', buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    @staticmethod
    def _filter_dir(path: Path, path_filter: List) -> List[Path]:
        """Recursively crawl over path and filter."""
        result = []
        for item in path.iterdir():
            if item.name in path_filter:
                continue
            if item.name.startswith('.'):
                continue
            if item.is_dir():
                result.extend(VersionRepacker._filter_dir(item, path_filter))
            else:
                result.append(item)
        return result

    def process(self):
        if (self.version_path / "pyproject.toml").exists():
            self._print(
                ("This cannot run on OpenPype sources. "
                 "Please run it on extracted version."), 1)
            return
        self._print(f"Rehashing and zipping {self.version_path}")
        version = OpenPypeVersion.version_in_str(self.version_path.name)
        if not version:
            self._print("Cannot get version from directory", 1)
            return

        self._print(f"Detected version is {version}")
        # replace version in version.py
        self._replace_version(version, self.version_path)
        self._print("Recalculating checksums ...", 2)

        checksums = []

        file_list = VersionRepacker._filter_dir(self.version_path, [])
        progress_bar = enlighten.Counter(
            total=len(file_list), desc="Calculating checksums",
            nits="%", color="green")
        for file in file_list:
            checksums.append((
                VersionRepacker.sha256sum(file.as_posix()),
                file.resolve().relative_to(self.version_path),
                file
            ))
            progress_bar.update()
        progress_bar.close()

        progress_bar = enlighten.Counter(
            total=len(checksums), desc="Zipping directory",
            nits="%", color=(56, 211, 159))

        zip_filename = self.zip_path / f"openpype-v{version}.zip"
        with ZipFile(zip_filename, "w") as zip_file:

            for item in checksums:
                if item[1].as_posix() == "checksums":
                    progress_bar.update()
                    continue
                zip_file.write(item[2], item[1])
                progress_bar.update()

            checksums_str = ""
            for c in checksums:
                file_str = c[1]
                if platform.system().lower() == "windows":
                    file_str = c[1].as_posix().replace("\\", "/")
                checksums_str += "{}:{}\n".format(c[0], file_str)
            zip_file.writestr("checksums", checksums_str)
            # test if zip is ok
            zip_file.testzip()
        self._print(f"All done, you can find new zip here: {zip_filename}")

    @staticmethod
    def _replace_version(version: OpenPypeVersion, path: Path):
        """Replace version in version.py.

        Args:
            version (OpenPypeVersion): OpenPype version to set
            path (Path): Path to unzipped version.

        """
        with open(path / "openpype" / "version.py", "r") as op_version_file:
            replacement = ""

            for line in op_version_file:
                stripped_line = line.strip()
                if stripped_line.strip().startswith("__version__ ="):
                    line = f'__version__ = "{version}"\n'
                replacement += line

        with open(path / "openpype" / "version.py", "w") as op_version_file:
            op_version_file.write(replacement)


if __name__ == '__main__':
    print(sys.argv[1])
    version_packer = VersionRepacker(sys.argv[1])
    version_packer.process()
