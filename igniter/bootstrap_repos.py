# -*- coding: utf-8 -*-
"""Bootstrap OpenPype repositories."""
from __future__ import annotations
import logging as log
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Union, Callable, List, Tuple
import hashlib
import platform

from zipfile import ZipFile, BadZipFile

from appdirs import user_data_dir
from speedcopy import copyfile
import semver

from .user_settings import (
    OpenPypeSecureRegistry,
    OpenPypeSettingsRegistry
)
from .tools import (
    get_openpype_global_settings,
    get_openpype_path_from_settings,
    get_expected_studio_version_str
)


LOG_INFO = 0
LOG_WARNING = 1
LOG_ERROR = 3


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


class OpenPypeVersion(semver.VersionInfo):
    """Class for storing information about OpenPype version.

    Attributes:
        staging (bool): True if it is staging version
        path (str): path to OpenPype

    """
    staging = False
    path = None
    _VERSION_REGEX = re.compile(r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")  # noqa: E501
    _installed_version = None

    def __init__(self, *args, **kwargs):
        """Create OpenPype version.

        .. deprecated:: 3.0.0-rc.2
            `client` and `variant` are removed.


        Args:
            major (int): version when you make incompatible API changes.
            minor (int): version when you add functionality in a
                backwards-compatible manner.
            patch (int): version when you make backwards-compatible bug fixes.
            prerelease (str): an optional prerelease string
            build (str): an optional build string
            version (str): if set, it will be parsed and will override
                parameters like `major`, `minor` and so on.
            staging (bool): set to True if version is staging.
            path (Path): path to version location.

        """
        self.path = None
        self.staging = False

        if "version" in kwargs.keys():
            if not kwargs.get("version"):
                raise ValueError("Invalid version specified")
            v = OpenPypeVersion.parse(kwargs.get("version"))
            kwargs["major"] = v.major
            kwargs["minor"] = v.minor
            kwargs["patch"] = v.patch
            kwargs["prerelease"] = v.prerelease
            kwargs["build"] = v.build
            kwargs.pop("version")

        if kwargs.get("path"):
            if isinstance(kwargs.get("path"), str):
                self.path = Path(kwargs.get("path"))
            elif isinstance(kwargs.get("path"), Path):
                self.path = kwargs.get("path")
            else:
                raise TypeError("Path must be str or Path")
            kwargs.pop("path")

        if "path" in kwargs.keys():
            kwargs.pop("path")

        if kwargs.get("staging"):
            self.staging = kwargs.get("staging", False)
            kwargs.pop("staging")

        if "staging" in kwargs.keys():
            kwargs.pop("staging")

        if self.staging:
            if kwargs.get("build"):
                if "staging" not in kwargs.get("build"):
                    kwargs["build"] = "{}-staging".format(kwargs.get("build"))
            else:
                kwargs["build"] = "staging"

        if kwargs.get("build") and "staging" in kwargs.get("build", ""):
            self.staging = True

        super().__init__(*args, **kwargs)

    def __eq__(self, other):
        result = super().__eq__(other)
        return bool(result and self.staging == other.staging)

    def __repr__(self):
        return "<{}: {} - path={}>".format(
            self.__class__.__name__, str(self), self.path)

    def __lt__(self, other: OpenPypeVersion):
        result = super().__lt__(other)
        # prefer path over no path
        if self == other and not self.path and other.path:
            return True

        if self == other and self.path and other.path and \
                other.path.is_dir() and self.path.is_file():
            return True

        if self.finalize_version() == other.finalize_version() and \
                self.prerelease == other.prerelease and \
                self.is_staging() and not other.is_staging():
            return True

        return result

    def set_staging(self) -> OpenPypeVersion:
        """Set version as staging and return it.

        This will preserve current one.

        Returns:
            OpenPypeVersion: Set as staging.

        """
        if self.staging:
            return self
        return self.replace(parts={"build": f"{self.build}-staging"})

    def set_production(self) -> OpenPypeVersion:
        """Set version as production and return it.

        This will preserve current one.

        Returns:
            OpenPypeVersion: Set as production.

        """
        if not self.staging:
            return self
        return self.replace(
            parts={"build": self.build.replace("-staging", "")})

    def is_staging(self) -> bool:
        """Test if current version is staging one."""
        return self.staging

    def get_main_version(self) -> str:
        """Return main version component.

        This returns x.x.x part of version from possibly more complex one
        like x.x.x-foo-bar.

        .. deprecated:: 3.0.0-rc.2
            use `finalize_version()` instead.
        Returns:
            str: main version component

        """
        return str(self.finalize_version())

    @staticmethod
    def version_in_str(string: str) -> Union[None, OpenPypeVersion]:
        """Find OpenPype version in given string.

        Args:
            string (str):  string to search.

        Returns:
            OpenPypeVersion: of detected or None.

        """
        m = re.search(OpenPypeVersion._VERSION_REGEX, string)
        if not m:
            return None
        version = OpenPypeVersion.parse(string[m.start():m.end()])
        if "staging" in string[m.start():m.end()]:
            version.staging = True
        return version

    @classmethod
    def parse(cls, version):
        """Extends parse to handle ta handle staging variant."""
        v = super().parse(version)
        openpype_version = cls(major=v.major, minor=v.minor,
                               patch=v.patch, prerelease=v.prerelease,
                               build=v.build)
        if v.build and "staging" in v.build:
            openpype_version.staging = True
        return openpype_version

    def __hash__(self):
        if self.path:
            return hash(self.path)
        else:
            return hash(str(self))

    @staticmethod
    def is_version_in_dir(
            dir_item: Path, version: OpenPypeVersion) -> Tuple[bool, str]:
        """Test if path item is OpenPype version matching detected version.

        If item is directory that might (based on it's name)
        contain OpenPype version, check if it really does contain
        OpenPype and that their versions matches.

        Args:
            dir_item (Path): Directory to test.
            version (OpenPypeVersion): OpenPype version detected
                from name.

        Returns:
            Tuple: State and reason, True if it is valid OpenPype version,
                   False otherwise.

        """
        try:
            # add one 'openpype' level as inside dir there should
            # be many other repositories.
            version_str = OpenPypeVersion.get_version_string_from_directory(
                dir_item)  # noqa: E501
            version_check = OpenPypeVersion(version=version_str)
        except ValueError:
            return False, f"cannot determine version from {dir_item}"

        version_main = version_check.get_main_version()
        detected_main = version.get_main_version()
        if version_main != detected_main:
            return False, (f"dir version ({version}) and "
                           f"its content version ({version_check}) "
                           "doesn't match. Skipping.")
        return True, "Versions match"

    @staticmethod
    def is_version_in_zip(
            zip_item: Path, version: OpenPypeVersion) -> Tuple[bool, str]:
        """Test if zip path is OpenPype version matching detected version.

        Open zip file, look inside and parse version from OpenPype
        inside it. If there is none, or it is different from
        version specified in file name, skip it.

        Args:
            zip_item (Path): Zip file to test.
            version (OpenPypeVersion): Pype version detected
                from name.

        Returns:
           Tuple: State and reason, True if it is valid OpenPype version,
                False otherwise.

        """
        # skip non-zip files
        if zip_item.suffix.lower() != ".zip":
            return False, "Not a zip"

        try:
            with ZipFile(zip_item, "r") as zip_file:
                with zip_file.open(
                        "openpype/version.py") as version_file:
                    zip_version = {}
                    exec(version_file.read(), zip_version)
                    try:
                        version_check = OpenPypeVersion(
                            version=zip_version["__version__"])
                    except ValueError as e:
                        return False, str(e)

                    version_main = version_check.get_main_version()  #
                    # noqa: E501
                    detected_main = version.get_main_version()
                    # noqa: E501

                    if version_main != detected_main:
                        return False, (f"zip version ({version}) "
                                       f"and its content version "
                                       f"({version_check}) "
                                       "doesn't match. Skipping.")
        except BadZipFile:
            return False, f"{zip_item} is not a zip file"
        except KeyError:
            return False, "Zip does not contain OpenPype"
        return True, "Versions match"

    @staticmethod
    def get_version_string_from_directory(repo_dir: Path) -> Union[str, None]:
        """Get version of OpenPype in given directory.

        Note: in frozen OpenPype installed in user data dir, this must point
        one level deeper as it is:
        `openpype-version-v3.0.0/openpype/version.py`

        Args:
            repo_dir (Path): Path to OpenPype repo.

        Returns:
            str: version string.
            None: if OpenPype is not found.

        """
        # try to find version
        version_file = Path(repo_dir) / "openpype" / "version.py"
        if not version_file.exists():
            return None

        version = {}
        with version_file.open("r") as fp:
            exec(fp.read(), version)

        return version['__version__']

    @classmethod
    def get_openpype_path(cls):
        """Path to openpype zip directory.

        Path can be set through environment variable 'OPENPYPE_PATH' which
        is set during start of OpenPype if is not available.
        """
        return os.getenv("OPENPYPE_PATH")

    @classmethod
    def openpype_path_is_set(cls):
        """Path to OpenPype zip directory is set."""
        if cls.get_openpype_path():
            return True
        return False

    @classmethod
    def openpype_path_is_accessible(cls):
        """Path to OpenPype zip directory is accessible.

        Exists for this machine.
        """
        # First check if is set
        if not cls.openpype_path_is_set():
            return False

        # Validate existence
        if Path(cls.get_openpype_path()).exists():
            return True
        return False

    @classmethod
    def get_local_versions(
        cls, production: bool = None, staging: bool = None
    ) -> List:
        """Get all versions available on this machine.

        Arguments give ability to specify if filtering is needed. If both
        arguments are set to None all found versions are returned.

        Args:
            production (bool): Return production versions.
            staging (bool): Return staging versions.
        """
        # Return all local versions if arguments are set to None
        if production is None and staging is None:
            production = True
            staging = True

        elif production is None and not staging:
            production = True

        elif staging is None and not production:
            staging = True

        # Just return empty output if both are disabled
        if not production and not staging:
            return []

        dir_to_search = Path(user_data_dir("openpype", "pypeclub"))
        versions = OpenPypeVersion.get_versions_from_directory(
            dir_to_search
        )
        filtered_versions = []
        for version in versions:
            if version.is_staging():
                if staging:
                    filtered_versions.append(version)
            elif production:
                filtered_versions.append(version)
        return list(sorted(set(filtered_versions)))

    @classmethod
    def get_remote_versions(
        cls, production: bool = None, staging: bool = None
    ) -> List:
        """Get all versions available in OpenPype Path.

        Arguments give ability to specify if filtering is needed. If both
        arguments are set to None all found versions are returned.

        Args:
            production (bool): Return production versions.
            staging (bool): Return staging versions.
        """
        # Return all local versions if arguments are set to None
        if production is None and staging is None:
            production = True
            staging = True

        elif production is None and not staging:
            production = True

        elif staging is None and not production:
            staging = True

        # Just return empty output if both are disabled
        if not production and not staging:
            return []

        dir_to_search = None
        if cls.openpype_path_is_accessible():
            dir_to_search = Path(cls.get_openpype_path())
        else:
            registry = OpenPypeSettingsRegistry()
            try:
                registry_dir = Path(str(registry.get_item("openPypePath")))
                if registry_dir.exists():
                    dir_to_search = registry_dir

            except ValueError:
                # nothing found in registry, we'll use data dir
                pass

        if not dir_to_search:
            return []

        versions = cls.get_versions_from_directory(dir_to_search)
        filtered_versions = []
        for version in versions:
            if version.is_staging():
                if staging:
                    filtered_versions.append(version)
            elif production:
                filtered_versions.append(version)
        return list(sorted(set(filtered_versions)))

    @staticmethod
    def get_versions_from_directory(openpype_dir: Path) -> List:
        """Get all detected OpenPype versions in directory.

        Args:
            openpype_dir (Path): Directory to scan.

        Returns:
            list of OpenPypeVersion

        Throws:
            ValueError: if invalid path is specified.

        """
        if not openpype_dir.exists() and not openpype_dir.is_dir():
            raise ValueError("specified directory is invalid")

        _openpype_versions = []
        # iterate over directory in first level and find all that might
        # contain OpenPype.
        for item in openpype_dir.iterdir():

            # if file, strip extension, in case of dir not.
            name = item.name if item.is_dir() else item.stem
            result = OpenPypeVersion.version_in_str(name)

            if result:
                detected_version: OpenPypeVersion
                detected_version = result

                if item.is_dir() and not OpenPypeVersion.is_version_in_dir(
                        item, detected_version
                )[0]:
                    continue

                if item.is_file() and not OpenPypeVersion.is_version_in_zip(
                        item, detected_version
                )[0]:
                    continue

                detected_version.path = item
                _openpype_versions.append(detected_version)

        return sorted(_openpype_versions)

    @staticmethod
    def get_installed_version_str() -> str:
        """Get version of local OpenPype."""

        version = {}
        path = Path(os.environ["OPENPYPE_ROOT"]) / "openpype" / "version.py"
        with open(path, "r") as fp:
            exec(fp.read(), version)
        return version["__version__"]

    @classmethod
    def get_installed_version(cls):
        """Get version of OpenPype inside build."""
        if cls._installed_version is None:
            installed_version_str = cls.get_installed_version_str()
            if installed_version_str:
                cls._installed_version = OpenPypeVersion(
                    version=installed_version_str,
                    path=Path(os.environ["OPENPYPE_ROOT"])
                )
        return cls._installed_version

    @staticmethod
    def get_latest_version(
        staging: bool = False,
        local: bool = None,
        remote: bool = None
    ) -> OpenPypeVersion:
        """Get latest available version.

        The version does not contain information about path and source.

        This is utility version to get latest version from all found. Build
        version is not listed if staging is enabled.

        Arguments 'local' and 'remote' define if local and remote repository
        versions are used. All versions are used if both are not set (or set
        to 'None'). If only one of them is set to 'True' the other is disabled.
        It is possible to set both to 'True' (same as both set to None) and to
        'False' in that case only build version can be used.

        Args:
            staging (bool, optional): List staging versions if True.
            local (bool, optional): List local versions if True.
            remote (bool, optional): List remote versions if True.
        """
        if local is None and remote is None:
            local = True
            remote = True

        elif local is None and not remote:
            local = True

        elif remote is None and not local:
            remote = True

        installed_version = OpenPypeVersion.get_installed_version()
        local_versions = []
        remote_versions = []
        if local:
            local_versions = OpenPypeVersion.get_local_versions(
                staging=staging
            )
        if remote:
            remote_versions = OpenPypeVersion.get_remote_versions(
                staging=staging
            )
        all_versions = local_versions + remote_versions
        if not staging:
            all_versions.append(installed_version)

        if not all_versions:
            return None

        all_versions.sort()
        return all_versions[-1]

    @classmethod
    def get_expected_studio_version(cls, staging=False, global_settings=None):
        """Expected OpenPype version that should be used at the moment.

        If version is not defined in settings the latest found version is
        used.

        Using precached global settings is needed for usage inside OpenPype.

        Args:
            staging (bool): Staging version or production version.
            global_settings (dict): Optional precached global settings.

        Returns:
            OpenPypeVersion: Version that should be used.
        """
        result = get_expected_studio_version_str(staging, global_settings)
        if not result:
            return None
        return OpenPypeVersion(version=result)


class BootstrapRepos:
    """Class for bootstrapping local OpenPype installation.

    Attributes:
        data_dir (Path): local OpenPype installation directory.
        live_repo_dir (Path): path to repos directory if running live,
            otherwise `None`.
        registry (OpenPypeSettingsRegistry): OpenPype registry object.
        zip_filter (list): List of files to exclude from zip
        openpype_filter (list): list of top level directories to
            include in zip in OpenPype repository.

    """

    def __init__(self, progress_callback: Callable = None, message=None):
        """Constructor.

        Args:
            progress_callback (callable): Optional callback method to report
                progress.
            message (QtCore.Signal, optional): Signal to report messages back.

        """
        # vendor and app used to construct user data dir
        self._vendor = "pypeclub"
        self._app = "openpype"
        self._log = log.getLogger(str(__class__))
        self.data_dir = Path(user_data_dir(self._app, self._vendor))
        self.secure_registry = OpenPypeSecureRegistry("mongodb")
        self.registry = OpenPypeSettingsRegistry()
        self.zip_filter = [".pyc", "__pycache__"]
        self.openpype_filter = [
            "openpype", "schema", "LICENSE"
        ]
        self._message = message

        # dummy progress reporter
        def empty_progress(x: int):
            """Progress callback dummy."""
            return x

        if not progress_callback:
            progress_callback = empty_progress
        self._progress_callback = progress_callback

        if getattr(sys, "frozen", False):
            self.live_repo_dir = Path(sys.executable).parent
        else:
            self.live_repo_dir = Path(Path(__file__).parent / "..")

    @staticmethod
    def get_version_path_from_list(
            version: str, version_list: list) -> Union[Path, None]:
        """Get path for specific version in list of OpenPype versions.

        Args:
            version (str): Version string to look for (1.2.4+staging)
            version_list (list of OpenPypeVersion): list of version to search.

        Returns:
            Path: Path to given version.

        """
        for v in version_list:
            if str(v) == version:
                return v.path
        return None

    @staticmethod
    def get_version(repo_dir: Path) -> Union[str, None]:
        """Get version of OpenPype in given directory.

        Note: in frozen OpenPype installed in user data dir, this must point
        one level deeper as it is:
        `openpype-version-v3.0.0/openpype/version.py`

        Args:
            repo_dir (Path): Path to OpenPype repo.

        Returns:
            str: version string.
            None: if OpenPype is not found.

        """
        # try to find version
        version_file = Path(repo_dir) / "openpype" / "version.py"
        if not version_file.exists():
            return None

        version = {}
        with version_file.open("r") as fp:
            exec(fp.read(), version)

        return version['__version__']

    def create_version_from_live_code(
            self, repo_dir: Path = None) -> Union[OpenPypeVersion, None]:
        """Copy zip created from OpenPype repositories to user data dir.

        This detect OpenPype version either in local "live" OpenPype
        repository or in user provided path. Then it will zip it in temporary
        directory and finally it will move it to destination which is user
        data directory. Existing files will be replaced.

        Args:
            repo_dir (Path, optional): Path to OpenPype repository.

        Returns:
            Path: path of installed repository file.

        """
        # if repo dir is not set, we detect local "live" OpenPype repository
        # version and use it as a source. Otherwise repo_dir is user
        # entered location.
        if not repo_dir:
            version = OpenPypeVersion.get_installed_version_str()
            repo_dir = self.live_repo_dir
        else:
            version = self.get_version(repo_dir)

        if not version:
            self._print("OpenPype not found.", LOG_ERROR)
            return

        # create destination directory
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)

        # create zip inside temporary directory.
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = \
                Path(temp_dir) / f"openpype-v{version}.zip"
            self._print(f"creating zip: {temp_zip}")

            self._create_openpype_zip(temp_zip, repo_dir)
            if not os.path.exists(temp_zip):
                self._print("make archive failed.", LOG_ERROR)
                return None

            destination = self._move_zip_to_data_dir(temp_zip)

        return OpenPypeVersion(version=version, path=Path(destination))

    def _move_zip_to_data_dir(self, zip_file) -> Union[None, Path]:
        """Move zip with OpenPype version to user data directory.

        Args:
            zip_file (Path): Path to zip file.

        Returns:
            None if move fails.
            Path to moved zip on success.

        """
        destination = self.data_dir / zip_file.name

        if destination.exists():
            self._print(
                f"Destination file {destination} exists, removing.",
                LOG_WARNING)
            try:
                destination.unlink()
            except Exception as e:
                self._print(str(e), LOG_ERROR, exc_info=True)
                return None
        try:
            shutil.move(zip_file.as_posix(), self.data_dir.as_posix())
        except shutil.Error as e:
            self._print(str(e), LOG_ERROR, exc_info=True)
            return None

        return destination

    def _filter_dir(self, path: Path, path_filter: List) -> List[Path]:
        """Recursively crawl over path and filter."""
        result = []
        for item in path.iterdir():
            if item.name in path_filter:
                continue
            if item.name.startswith('.'):
                continue
            if item.is_dir():
                result.extend(self._filter_dir(item, path_filter))
            else:
                result.append(item)
        return result

    def create_version_from_frozen_code(self) -> Union[None, OpenPypeVersion]:
        """Create OpenPype version from *frozen* code distributed by installer.

        This should be real edge case for those wanting to try out OpenPype
        without setting up whole infrastructure but is strongly discouraged
        in studio setup as this use local version independent of others
        that can be out of date.

        Returns:
            :class:`OpenPypeVersion` zip file to be installed.

        """
        frozen_root = Path(sys.executable).parent

        openpype_list = []
        for f in self.openpype_filter:
            if (frozen_root / f).is_dir():
                openpype_list += self._filter_dir(
                    frozen_root / f, self.zip_filter)
            else:
                openpype_list.append(frozen_root / f)

        version = self.get_version(frozen_root)

        # create zip inside temporary directory.
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = \
                Path(temp_dir) / f"openpype-v{version}.zip"
            self._print(f"creating zip: {temp_zip}")

            with ZipFile(temp_zip, "w") as zip_file:
                progress = 0
                openpype_inc = 98.0 / float(len(openpype_list))
                file: Path
                for file in openpype_list:
                    progress += openpype_inc
                    self._progress_callback(int(progress))

                    arc_name = file.relative_to(frozen_root.parent)
                    # we need to replace first part of path which starts with
                    # something like `exe.win/linux....` with `openpype` as
                    # this is expected by OpenPype in zip archive.
                    arc_name = Path().joinpath(*arc_name.parts[1:])
                    zip_file.write(file, arc_name)

            destination = self._move_zip_to_data_dir(temp_zip)

        return OpenPypeVersion(version=version, path=destination)

    def _create_openpype_zip(self, zip_path: Path, openpype_path: Path) -> None:
        """Pack repositories and OpenPype into zip.

        We are using :mod:`zipfile` instead :meth:`shutil.make_archive`
        because we need to decide what file and directories to include in zip
        and what not. They are determined by :attr:`zip_filter` on file level
        and :attr:`openpype_filter` on top level directory in OpenPype
        repository.

        Args:
            zip_path (Path): Path to zip file.
            openpype_path (Path): Path to OpenPype sources.

        """
        # get filtered list of file in Pype repository
        # openpype_list = self._filter_dir(openpype_path, self.zip_filter)
        openpype_list = []
        for f in self.openpype_filter:
            if (openpype_path / f).is_dir():
                openpype_list += self._filter_dir(
                    openpype_path / f, self.zip_filter)
            else:
                openpype_list.append(openpype_path / f)

        openpype_files = len(openpype_list)

        openpype_inc = 98.0 / float(openpype_files)

        with ZipFile(zip_path, "w") as zip_file:
            progress = 0
            openpype_root = openpype_path.resolve()
            # generate list of filtered paths
            dir_filter = [openpype_root / f for f in self.openpype_filter]
            checksums = []

            file: Path
            for file in openpype_list:
                progress += openpype_inc
                self._progress_callback(int(progress))

                # if file resides in filtered path, skip it
                is_inside = None
                df: Path
                for df in dir_filter:
                    try:
                        is_inside = file.resolve().relative_to(df)
                    except ValueError:
                        pass

                if not is_inside:
                    continue

                processed_path = file
                self._print(f"- processing {processed_path}")

                checksums.append(
                    (
                        sha256sum(file.as_posix()),
                        file.resolve().relative_to(openpype_root)
                    )
                )
                zip_file.write(
                    file, file.resolve().relative_to(openpype_root))

            checksums_str = ""
            for c in checksums:
                file_str = c[1]
                if platform.system().lower() == "windows":
                    file_str = c[1].as_posix().replace("\\", "/")
                checksums_str += "{}:{}\n".format(c[0], file_str)
            zip_file.writestr("checksums", checksums_str)
            # test if zip is ok
            zip_file.testzip()
            self._progress_callback(100)

    def validate_openpype_version(self, path: Path) -> tuple:
        """Validate version directory or zip file.

        This will load `checksums` file if present, calculate checksums
        of existing files in given path and compare. It will also compare
        lists of files together for missing files.

        Args:
            path (Path): Path to OpenPype version to validate.

        Returns:
            tuple(bool, str): with version validity as first item
                and string with reason as second.

        """
        if os.getenv("OPENPYPE_DONT_VALIDATE_VERSION"):
            return True, "Disabled validation"
        if not path.exists():
            return False, "Path doesn't exist"

        if path.is_file():
            return self._validate_zip(path)
        return self._validate_dir(path)

    @staticmethod
    def _validate_zip(path: Path) -> tuple:
        """Validate content of zip file."""
        with ZipFile(path, "r") as zip_file:
            # read checksums
            try:
                checksums_data = str(zip_file.read("checksums"))
            except IOError:
                # FIXME: This should be set to False sometimes in the future
                return True, "Cannot read checksums for archive."

            # split it to the list of tuples
            checksums = [
                tuple(line.split(":"))
                for line in checksums_data.split("\n") if line
            ]

            # get list of files in zip minus `checksums` file itself
            # and turn in to set to compare against list of files
            # from checksum file. If difference exists, something is
            # wrong
            files_in_zip = set(zip_file.namelist())
            files_in_zip.remove("checksums")
            files_in_checksum = {file[1] for file in checksums}
            diff = files_in_zip.difference(files_in_checksum)
            if diff:
                return False, f"Missing files {diff}"

            # calculate and compare checksums in the zip file
            for file_checksum, file_name in checksums:
                if platform.system().lower() == "windows":
                    file_name = file_name.replace("/", "\\")
                h = hashlib.sha256()
                try:
                    h.update(zip_file.read(file_name))
                except FileNotFoundError:
                    return False, f"Missing file [ {file_name} ]"
                if h.hexdigest() != file_checksum:
                    return False, f"Invalid checksum on {file_name}"

        return True, "All ok"

    @staticmethod
    def _validate_dir(path: Path) -> tuple:
        checksums_file = Path(path / "checksums")
        if not checksums_file.exists():
            # FIXME: This should be set to False sometimes in the future
            return True, "Cannot read checksums for archive."
        checksums_data = checksums_file.read_text()
        checksums = [
            tuple(line.split(":"))
            for line in checksums_data.split("\n") if line
        ]

        # compare file list against list of files from checksum file.
        # If difference exists, something is wrong and we invalidate directly
        files_in_dir = set(
            file.relative_to(path).as_posix()
            for file in path.iterdir() if file.is_file()
        )
        files_in_dir.remove("checksums")
        files_in_checksum = {file[1] for file in checksums}

        diff = files_in_dir.difference(files_in_checksum)
        if diff:
            return False, f"Missing files {diff}"

        # calculate and compare checksums
        for file_checksum, file_name in checksums:
            if platform.system().lower() == "windows":
                file_name = file_name.replace("/", "\\")
            try:
                current = sha256sum((path / file_name).as_posix())
            except FileNotFoundError:
                return False, f"Missing file [ {file_name} ]"

            if file_checksum != current:
                return False, f"Invalid checksum on {file_name}"

        return True, "All ok"

    @staticmethod
    def add_paths_from_archive(archive: Path) -> None:
        """Add first-level directory and 'repos' as paths to :mod:`sys.path`.

        This will enable Python to import OpenPype and modules in `repos`
        submodule directory in zip file.

        Adding to both `sys.path` and `PYTHONPATH`, skipping duplicates.

        Args:
            archive (Path): path to archive.

        .. deprecated:: 3.0
            we don't use zip archives directly

        """
        if not archive.is_file() and not archive.exists():
            raise ValueError("Archive is not file.")

        archive_path = str(archive)
        sys.path.insert(0, archive_path)
        pythonpath = os.getenv("PYTHONPATH", "")
        python_paths = pythonpath.split(os.pathsep)
        python_paths.insert(0, archive_path)

        os.environ["PYTHONPATH"] = os.pathsep.join(python_paths)

    @staticmethod
    def add_paths_from_directory(directory: Path) -> None:
        """Add repos first level directories as paths to :mod:`sys.path`.

        This works the same as :meth:`add_paths_from_archive` but in
        specified directory.

        Adding to both `sys.path` and `PYTHONPATH`, skipping duplicates.

        Args:
            directory (Path): path to directory.

        """

        sys.path.insert(0, directory.as_posix())

    @staticmethod
    def find_openpype_version(version, staging):
        if isinstance(version, str):
            version = OpenPypeVersion(version=version)

        installed_version = OpenPypeVersion.get_installed_version()
        if installed_version == version:
            return installed_version

        local_versions = OpenPypeVersion.get_local_versions(
            staging=staging, production=not staging
        )
        zip_version = None
        for local_version in local_versions:
            if local_version == version:
                if local_version.path.suffix.lower() == ".zip":
                    zip_version = local_version
                else:
                    return local_version

        if zip_version is not None:
            return zip_version

        remote_versions = OpenPypeVersion.get_remote_versions(
            staging=staging, production=not staging
        )
        for remote_version in remote_versions:
            if remote_version == version:
                return remote_version
        return None

    @staticmethod
    def find_latest_openpype_version(staging):
        installed_version = OpenPypeVersion.get_installed_version()
        local_versions = OpenPypeVersion.get_local_versions(
            staging=staging
        )
        remote_versions = OpenPypeVersion.get_remote_versions(
            staging=staging
        )
        all_versions = local_versions + remote_versions
        if not staging:
            all_versions.append(installed_version)

        if not all_versions:
            return None

        all_versions.sort()
        latest_version = all_versions[-1]
        if latest_version == installed_version:
            return latest_version

        if not latest_version.path.is_dir():
            for version in local_versions:
                if version == latest_version and version.path.is_dir():
                    latest_version = version
                    break
        return latest_version

    def find_openpype(
            self,
            openpype_path: Union[Path, str] = None,
            staging: bool = False,
            include_zips: bool = False) -> Union[List[OpenPypeVersion], None]:
        """Get ordered dict of detected OpenPype version.

        Resolution order for OpenPype is following:

            1) First we test for ``OPENPYPE_PATH`` environment variable
            2) We try to find ``openPypePath`` in registry setting
            3) We use user data directory

        Args:
            openpype_path (Path or str, optional): Try to find OpenPype on
                the given path or url.
            staging (bool, optional): Filter only staging version, skip them
                otherwise.
            include_zips (bool, optional): If set True it will try to find
                OpenPype in zip files in given directory.

        Returns:
            dict of Path: Dictionary of detected OpenPype version.
                 Key is version, value is path to zip file.

            None: if OpenPype is not found.

        Todo:
            implement git/url support as OpenPype location, so it would be
            possible to enter git url, OpenPype would check it out and if it is
            ok install it as normal version.

        """
        if openpype_path and not isinstance(openpype_path, Path):
            raise NotImplementedError(
                ("Finding OpenPype in non-filesystem locations is"
                 " not implemented yet."))

        dir_to_search = self.data_dir
        user_versions = self.get_openpype_versions(self.data_dir, staging)
        # if we have openpype_path specified, search only there.
        if openpype_path:
            dir_to_search = openpype_path
        else:
            if os.getenv("OPENPYPE_PATH"):
                if Path(os.getenv("OPENPYPE_PATH")).exists():
                    dir_to_search = Path(os.getenv("OPENPYPE_PATH"))
            else:
                try:
                    registry_dir = Path(
                        str(self.registry.get_item("openPypePath")))
                    if registry_dir.exists():
                        dir_to_search = registry_dir

                except ValueError:
                    # nothing found in registry, we'll use data dir
                    pass

        openpype_versions = self.get_openpype_versions(dir_to_search, staging)
        openpype_versions += user_versions

        # remove zip file version if needed.
        if not include_zips:
            openpype_versions = [
                v for v in openpype_versions if v.path.suffix != ".zip"
            ]

        # remove duplicates
        openpype_versions = sorted(list(set(openpype_versions)))

        return openpype_versions

    def process_entered_location(self, location: str) -> Union[Path, None]:
        """Process user entered location string.

        It decides if location string is mongodb url or path.
        If it is mongodb url, it will connect and load ``OPENPYPE_PATH`` from
        there and use it as path to OpenPype. In it is _not_ mongodb url, it
        is assumed we have a path, this is tested and zip file is
        produced and installed using :meth:`create_version_from_live_code`.

        Args:
            location (str): User entered location.

        Returns:
            Path: to OpenPype zip produced from this location.
            None: Zipping failed.

        """
        openpype_path = None
        # try to get OpenPype path from mongo.
        if location.startswith("mongodb"):
            global_settings = get_openpype_global_settings(location)
            openpype_path = get_openpype_path_from_settings(global_settings)
            if not openpype_path:
                self._print("cannot find OPENPYPE_PATH in settings.")
                return None

        # if not successful, consider location to be fs path.
        if not openpype_path:
            openpype_path = Path(location)

        # test if this path does exist.
        if not openpype_path.exists():
            self._print(f"{openpype_path} doesn't exists.")
            return None

        # test if entered path isn't user data dir
        if self.data_dir == openpype_path:
            self._print("cannot point to user data dir", LOG_ERROR)
            return None

        # find openpype zip files in location. There can be
        # either "live" OpenPype repository, or multiple zip files or even
        # multiple OpenPype version directories. This process looks into zip
        # files and directories and tries to parse `version.py` file.
        versions = self.find_openpype(openpype_path, include_zips=True)
        if versions:
            self._print(f"found OpenPype in [ {openpype_path} ]")
            self._print(f"latest version found is [ {versions[-1]} ]")

            return self.install_version(versions[-1])

        # if we got here, it means that location is "live"
        # OpenPype repository. We'll create zip from it and move it to user
        # data dir.
        live_openpype = self.create_version_from_live_code(openpype_path)
        if not live_openpype.path.exists():
            self._print(f"installing zip {live_openpype} failed.", LOG_ERROR)
            return None
        # install it
        return self.install_version(live_openpype)

    def _print(self,
               message: str,
               level: int = LOG_INFO,
               exc_info: bool = False):
        """Helper function passing logs to UI and to logger.

        Supporting 3 levels of logs defined with `LOG_INFO`, `LOG_WARNING` and
        `LOG_ERROR` constants.

        Args:
            message (str): Message to log.
            level (int, optional): Log level to use.
            exc_info (bool, optional): Exception info object to pass to logger.

        """
        if self._message:
            self._message.emit(message, level == LOG_ERROR)

        if level == LOG_WARNING:
            self._log.warning(message, exc_info=exc_info)
            return
        if level == LOG_ERROR:
            self._log.error(message, exc_info=exc_info)
            return
        self._log.info(message, exc_info=exc_info)

    def extract_openpype(self, version: OpenPypeVersion) -> Union[Path, None]:
        """Extract zipped OpenPype version to user data directory.

        Args:
            version (OpenPypeVersion): Version of OpenPype.

        Returns:
            Path: path to extracted version.
            None: if something failed.

        """
        if not version.path:
            raise ValueError(
                f"version {version} is not associated with any file")

        destination = self.data_dir / version.path.stem
        if destination.exists():
            assert destination.is_dir()
            try:
                shutil.rmtree(destination)
            except OSError as e:
                msg = f"!!! Cannot remove already existing {destination}"
                self._print(msg, LOG_ERROR, exc_info=True)
                raise e

        destination.mkdir(parents=True)

        # extract zip there
        self._print("Extracting zip to destination ...")
        with ZipFile(version.path, "r") as zip_ref:
            zip_ref.extractall(destination)

        self._print(f"Installed as {version.path.stem}")

        return destination

    def is_inside_user_data(self, path: Path) -> bool:
        """Test if version is located in user data dir.

        Args:
            path (Path) Path to test.

        Returns:
            True if path is inside user data dir.

        """
        is_inside = False
        try:
            is_inside = path.resolve().relative_to(
                self.data_dir)
        except ValueError:
            # if relative path cannot be calculated, OpenPype version is not
            # inside user data dir
            pass
        return is_inside

    def install_version(self,
                        openpype_version: OpenPypeVersion,
                        force: bool = False) -> Path:
        """Install OpenPype version to user data directory.

        Args:
            openpype_version (OpenPypeVersion): OpenPype version to install.
            force (bool, optional): Force overwrite existing version.

        Returns:
            Path: Path to installed OpenPype.

        Raises:
            OpenPypeVersionExists: If not forced and this version already exist
                in user data directory.
            OpenPypeVersionInvalid: If version to install is invalid.
            OpenPypeVersionIOError: If copying or zipping fail.

        """
        if self.is_inside_user_data(openpype_version.path) and not openpype_version.path.is_file():  # noqa
            raise OpenPypeVersionExists(
                "OpenPype already inside user data dir")

        # determine destination directory name
        # for zip file strip suffix, in case of dir use whole dir name
        if openpype_version.path.is_dir():
            dir_name = openpype_version.path.name
        else:
            dir_name = openpype_version.path.stem

        destination = self.data_dir / dir_name

        # test if destination directory already exist, if so lets delete it.
        if destination.exists() and force:
            self._print("removing existing directory")
            try:
                shutil.rmtree(destination)
            except OSError as e:
                self._print(
                    f"cannot remove already existing {destination}",
                    LOG_ERROR, exc_info=True)
                raise OpenPypeVersionIOError(
                    f"cannot remove existing {destination}") from e
        elif destination.exists() and not force:
            self._print("destination directory already exists")
            raise OpenPypeVersionExists(f"{destination} already exist.")
        else:
            # create destination parent directories even if they don't exist.
            destination.mkdir(parents=True)

        remove_source_file = False
        # version is directory
        if openpype_version.path.is_dir():
            # create zip inside temporary directory.
            self._print("Creating zip from directory ...")
            self._progress_callback(0)
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_zip = \
                    Path(temp_dir) / f"openpype-v{openpype_version}.zip"
                self._print(f"creating zip: {temp_zip}")

                self._create_openpype_zip(temp_zip, openpype_version.path)
                if not os.path.exists(temp_zip):
                    self._print("make archive failed.", LOG_ERROR)
                    raise OpenPypeVersionIOError("Zip creation failed.")

                # set zip as version source
                openpype_version.path = temp_zip

                if self.is_inside_user_data(openpype_version.path):
                    raise OpenPypeVersionInvalid(
                        "Version is in user data dir.")
                openpype_version.path = self._copy_zip(
                    openpype_version.path, destination)

        elif openpype_version.path.is_file():
            # check if file is zip (by extension)
            if openpype_version.path.suffix.lower() != ".zip":
                raise OpenPypeVersionInvalid("Invalid file format")

            if not self.is_inside_user_data(openpype_version.path):
                self._progress_callback(35)
                openpype_version.path = self._copy_zip(
                    openpype_version.path, destination)
                # Mark zip to be deleted when done
                remove_source_file = True

        # extract zip there
        self._print("extracting zip to destination ...")
        with ZipFile(openpype_version.path, "r") as zip_ref:
            self._progress_callback(75)
            zip_ref.extractall(destination)
            self._progress_callback(100)

        # Remove zip file copied to local app data
        if remove_source_file:
            os.remove(openpype_version.path)

        return destination

    def _copy_zip(self, source: Path, destination: Path) -> Path:
        try:
            # copy file to destination
            self._print("Copying zip to destination ...")
            _destination_zip = destination.parent / source.name  # noqa: E501
            copyfile(
                source.as_posix(),
                _destination_zip.as_posix())
        except OSError as e:
            self._print(
                "cannot copy version to user data directory", LOG_ERROR,
                exc_info=True)
            raise OpenPypeVersionIOError((
                f"can't copy version {source.as_posix()} "
                f"to destination {destination.parent.as_posix()}")) from e
        return _destination_zip

    def _is_openpype_in_dir(self,
                            dir_item: Path,
                            detected_version: OpenPypeVersion) -> bool:
        """Test if path item is OpenPype version matching detected version.

        If item is directory that might (based on it's name)
        contain OpenPype version, check if it really does contain
        OpenPype and that their versions matches.

        Args:
            dir_item (Path): Directory to test.
            detected_version (OpenPypeVersion): OpenPype version detected
                from name.

        Returns:
            True if it is valid OpenPype version, False otherwise.

        """
        try:
            # add one 'openpype' level as inside dir there should
            # be many other repositories.
            version_str = BootstrapRepos.get_version(dir_item)
            version_check = OpenPypeVersion(version=version_str)
        except ValueError:
            self._print(
                f"cannot determine version from {dir_item}", True)
            return False

        version_main = version_check.get_main_version()
        detected_main = detected_version.get_main_version()
        if version_main != detected_main:
            self._print(
                (f"dir version ({detected_version}) and "
                 f"its content version ({version_check}) "
                 "doesn't match. Skipping."))
            return False
        return True

    def _is_openpype_in_zip(self,
                            zip_item: Path,
                            detected_version: OpenPypeVersion) -> bool:
        """Test if zip path is OpenPype version matching detected version.

        Open zip file, look inside and parse version from OpenPype
        inside it. If there is none, or it is different from
        version specified in file name, skip it.

        Args:
            zip_item (Path): Zip file to test.
            detected_version (OpenPypeVersion): Pype version detected from
                name.

        Returns:
           True if it is valid OpenPype version, False otherwise.

        """
        # skip non-zip files
        if zip_item.suffix.lower() != ".zip":
            return False

        try:
            with ZipFile(zip_item, "r") as zip_file:
                with zip_file.open(
                        "openpype/version.py") as version_file:
                    zip_version = {}
                    exec(version_file.read(), zip_version)
                    try:
                        version_check = OpenPypeVersion(
                            version=zip_version["__version__"])
                    except ValueError as e:
                        self._print(str(e), True)
                        return False

                    version_main = version_check.get_main_version()  # noqa: E501
                    detected_main = detected_version.get_main_version()  # noqa: E501

                    if version_main != detected_main:
                        self._print(
                            (f"zip version ({detected_version}) "
                             f"and its content version "
                             f"({version_check}) "
                             "doesn't match. Skipping."), True)
                        return False
        except BadZipFile:
            self._print(f"{zip_item} is not a zip file", True)
            return False
        except KeyError:
            self._print("Zip does not contain OpenPype", True)
            return False
        return True

    def get_openpype_versions(self,
                              openpype_dir: Path,
                              staging: bool = False) -> list:
        """Get all detected OpenPype versions in directory.

        Args:
            openpype_dir (Path): Directory to scan.
            staging (bool, optional): Find staging versions if True.

        Returns:
            list of OpenPypeVersion

        Throws:
            ValueError: if invalid path is specified.

        """
        if not openpype_dir.exists() and not openpype_dir.is_dir():
            raise ValueError("specified directory is invalid")

        _openpype_versions = []
        # iterate over directory in first level and find all that might
        # contain OpenPype.
        for item in openpype_dir.iterdir():

            # if file, strip extension, in case of dir not.
            name = item.name if item.is_dir() else item.stem
            result = OpenPypeVersion.version_in_str(name)

            if result:
                detected_version: OpenPypeVersion
                detected_version = result

                if item.is_dir() and not self._is_openpype_in_dir(
                    item, detected_version
                ):
                    continue

                if item.is_file() and not self._is_openpype_in_zip(
                    item, detected_version
                ):
                    continue

                detected_version.path = item
                if staging and detected_version.is_staging():
                    _openpype_versions.append(detected_version)

                if not staging and not detected_version.is_staging():
                    _openpype_versions.append(detected_version)

        return sorted(_openpype_versions)


class OpenPypeVersionExists(Exception):
    """Exception for handling existing OpenPype version."""
    pass


class OpenPypeVersionInvalid(Exception):
    """Exception for handling invalid OpenPype version."""
    pass


class OpenPypeVersionIOError(Exception):
    """Exception for handling IO errors in OpenPype version."""
    pass
