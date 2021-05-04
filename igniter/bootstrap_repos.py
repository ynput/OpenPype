# -*- coding: utf-8 -*-
"""Bootstrap OpenPype repositories."""
import functools
import logging as log
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Union, Callable, List, Tuple
from zipfile import ZipFile, BadZipFile

from appdirs import user_data_dir
from speedcopy import copyfile

from .user_settings import (
    OpenPypeSecureRegistry,
    OpenPypeSettingsRegistry
)
from .tools import get_openpype_path_from_db


LOG_INFO = 0
LOG_WARNING = 1
LOG_ERROR = 3


@functools.total_ordering
class OpenPypeVersion:
    """Class for storing information about OpenPype version.

    Attributes:
        major (int): [1].2.3-client-variant
        minor (int): 1.[2].3-client-variant
        subversion (int): 1.2.[3]-client-variant
        client (str): 1.2.3-[client]-variant
        variant (str): 1.2.3-client-[variant]
        path (str): path to OpenPype

    """
    major = 0
    minor = 0
    subversion = 0
    variant = ""
    client = None
    path = None

    _version_regex = re.compile(
        r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<sub>\d+)(-(?P<var1>staging)|-(?P<client>.+)(-(?P<var2>staging)))?")  # noqa: E501

    @property
    def version(self):
        """return formatted version string."""
        return self._compose_version()

    @version.setter
    def version(self, val):
        decomposed = self._decompose_version(val)
        self.major = decomposed[0]
        self.minor = decomposed[1]
        self.subversion = decomposed[2]
        self.variant = decomposed[3]
        self.client = decomposed[4]

    def __init__(self, major: int = None, minor: int = None,
                 subversion: int = None, version: str = None,
                 variant: str = "", client: str = None,
                 path: Path = None):
        self.path = path

        if (
                major is None or minor is None or subversion is None
        ) and version is None:
            raise ValueError("Need version specified in some way.")
        if version:
            values = self._decompose_version(version)
            self.major = values[0]
            self.minor = values[1]
            self.subversion = values[2]
            self.variant = values[3]
            self.client = values[4]
        else:
            self.major = major
            self.minor = minor
            self.subversion = subversion
            # variant is set only if it is "staging", otherwise "production" is
            # implied and no need to mention it in version string.
            if variant == "staging":
                self.variant = variant
            self.client = client

    def _compose_version(self):
        version = "{}.{}.{}".format(self.major, self.minor, self.subversion)

        if self.client:
            version = "{}-{}".format(version, self.client)

        if self.variant == "staging":
            version = "{}-{}".format(version, self.variant)

        return version

    @classmethod
    def _decompose_version(cls, version_string: str) -> tuple:
        m = re.search(cls._version_regex, version_string)
        if not m:
            raise ValueError(
                "Cannot parse version string: {}".format(version_string))

        variant = None
        if m.group("var1") == "staging" or m.group("var2") == "staging":
            variant = "staging"

        client = m.group("client")

        return (int(m.group("major")), int(m.group("minor")),
                int(m.group("sub")), variant, client)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.version == other.version

    def __str__(self):
        return self.version

    def __repr__(self):
        return "{}, {}: {}".format(
            self.__class__.__name__, self.version, self.path)

    def __hash__(self):
        return hash(self.version)

    def __lt__(self, other):
        if (self.major, self.minor, self.subversion) < \
                (other.major, other.minor, other.subversion):
            return True

        # 1.2.3-staging < 1.2.3-client-staging
        if self.get_main_version() == other.get_main_version() and \
                not self.client and self.variant and \
                other.client and other.variant:
            return True

        # 1.2.3 < 1.2.3-staging
        if self.get_main_version() == other.get_main_version() and \
                not self.client and self.variant and \
                not other.client and not other.variant:
            return True

        # 1.2.3 < 1.2.3-client
        if self.get_main_version() == other.get_main_version() and \
                not self.client and not self.variant and \
                other.client and not other.variant:
            return True

        # 1.2.3 < 1.2.3-client-staging
        if self.get_main_version() == other.get_main_version() and \
                not self.client and not self.variant and other.client:
            return True

        # 1.2.3-client-staging < 1.2.3-client
        if self.get_main_version() == other.get_main_version() and \
                self.client and self.variant and \
                other.client and not other.variant:
            return True

        # prefer path over no path
        if self.version == other.version and \
                not self.path and other.path:
            return True

        # prefer path with dir over path with file
        return self.version == other.version and self.path and \
            other.path and self.path.is_file() and \
            other.path.is_dir()

    def is_staging(self) -> bool:
        """Test if current version is staging one."""
        return self.variant == "staging"

    def get_main_version(self) -> str:
        """Return main version component.

        This returns x.x.x part of version from possibly more complex one
        like x.x.x-foo-bar.

        Returns:
            str: main version component

        """
        return "{}.{}.{}".format(self.major, self.minor, self.subversion)

    @staticmethod
    def version_in_str(string: str) -> Tuple:
        """Find OpenPype version in given string.

        Args:
            string (str):  string to search.

        Returns:
            tuple: True/False and OpenPypeVersion if found.

        """
        try:
            result = OpenPypeVersion._decompose_version(string)
        except ValueError:
            return False, None
        return True, OpenPypeVersion(major=result[0],
                                     minor=result[1],
                                     subversion=result[2],
                                     variant=result[3],
                                     client=result[4])


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
            "openpype", "repos", "schema", "LICENSE"
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
            self.live_repo_dir = Path(sys.executable).parent / "repos"
        else:
            self.live_repo_dir = Path(Path(__file__).parent / ".." / "repos")

    @staticmethod
    def get_version_path_from_list(version: str, version_list: list) -> Path:
        """Get path for specific version in list of OpenPype versions.

        Args:
            version (str): Version string to look for (1.2.4-staging)
            version_list (list of OpenPypeVersion): list of version to search.

        Returns:
            Path: Path to given version.

        """
        for v in version_list:
            if str(v) == version:
                return v.path

    @staticmethod
    def get_local_live_version() -> str:
        """Get version of local OpenPype."""

        version = {}
        path = Path(os.environ["OPENPYPE_ROOT"]) / "openpype" / "version.py"
        with open(path, "r") as fp:
            exec(fp.read(), version)
        return version["__version__"]

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
            version = self.get_local_live_version()
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

            self._create_openpype_zip(temp_zip, repo_dir.parent)
            if not os.path.exists(temp_zip):
                self._print("make archive failed.", LOG_ERROR)
                return None

            destination = self._move_zip_to_data_dir(temp_zip)

        return OpenPypeVersion(version=version, path=destination)

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

                zip_file.write(file, file.relative_to(openpype_root))

            # test if zip is ok
            zip_file.testzip()
            self._progress_callback(100)

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

        with ZipFile(archive, "r") as zip_file:
            name_list = zip_file.namelist()

        roots = []
        paths = []
        for item in name_list:
            if not item.startswith("repos/"):
                continue

            root = item.split("/")[1]

            if root not in roots:
                roots.append(root)
                paths.append(
                    f"{archive}{os.path.sep}repos{os.path.sep}{root}")
                sys.path.insert(0, paths[-1])

        sys.path.insert(0, f"{archive}")
        pythonpath = os.getenv("PYTHONPATH", "")
        python_paths = pythonpath.split(os.pathsep)
        python_paths += paths

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
        directory /= "repos"
        if not directory.exists() and not directory.is_dir():
            raise ValueError("directory is invalid")

        roots = []
        for item in directory.iterdir():
            if item.is_dir():
                root = item.as_posix()
                if root not in roots:
                    roots.append(root)
                    sys.path.insert(0, root)

        pythonpath = os.getenv("PYTHONPATH", "")
        paths = pythonpath.split(os.pathsep)
        paths += roots

        os.environ["PYTHONPATH"] = os.pathsep.join(paths)

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

        # remove zip file version if needed.
        if not include_zips:
            openpype_versions = [
                v for v in openpype_versions if v.path.suffix != ".zip"
            ]

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
            openpype_path = get_openpype_path_from_db(location)
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
            try:
                destination.unlink()
            except OSError:
                msg = f"!!! Cannot remove already existing {destination}"
                self._print(msg, LOG_ERROR, exc_info=True)
                return None

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
            try:
                shutil.rmtree(destination)
            except OSError as e:
                self._print(
                    f"cannot remove already existing {destination}",
                    LOG_ERROR, exc_info=True)
                raise OpenPypeVersionIOError(
                    f"cannot remove existing {destination}") from e
        elif destination.exists() and not force:
            raise OpenPypeVersionExists(f"{destination} already exist.")
        else:
            # create destination parent directories even if they don't exist.
            destination.mkdir(parents=True)

        # version is directory
        if openpype_version.path.is_dir():
            # create zip inside temporary directory.
            self._print("Creating zip from directory ...")
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

        elif openpype_version.path.is_file():
            # check if file is zip (by extension)
            if openpype_version.path.suffix.lower() != ".zip":
                raise OpenPypeVersionInvalid("Invalid file format")

        if not self.is_inside_user_data(openpype_version.path):
            try:
                # copy file to destination
                self._print("Copying zip to destination ...")
                _destination_zip = destination.parent / openpype_version.path.name  # noqa: E501
                copyfile(
                    openpype_version.path.as_posix(),
                    _destination_zip.as_posix())
            except OSError as e:
                self._print(
                    "cannot copy version to user data directory", LOG_ERROR,
                    exc_info=True)
                raise OpenPypeVersionIOError((
                    f"can't copy version {openpype_version.path.as_posix()} "
                    f"to destination {destination.parent.as_posix()}")) from e

        # extract zip there
        self._print("extracting zip to destination ...")
        with ZipFile(openpype_version.path, "r") as zip_ref:
            zip_ref.extractall(destination)

        return destination

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
            detected_version (OpenPypeVersion): Pype version detected from name.

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
                    version_check = OpenPypeVersion(
                        version=zip_version["__version__"])

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

            if result[0]:
                detected_version: OpenPypeVersion
                detected_version = result[1]

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
