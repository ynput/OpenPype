# -*- coding: utf-8 -*-
"""Bootstrap Pype repositories."""
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

from .user_settings import PypeSettingsRegistry
from .tools import get_pype_path_from_db


LOG_INFO = 0
LOG_WARNING = 1
LOG_ERROR = 3


@functools.total_ordering
class PypeVersion:
    """Class for storing information about Pype version.

    Attributes:
        major (int): [1].2.3-client-variant
        minor (int): 1.[2].3-client-variant
        subversion (int): 1.2.[3]-client-variant
        client (str): 1.2.3-[client]-variant
        variant (str): 1.2.3-client-[variant]
        path (str): path to Pype

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
        """Find Pype version in given string.

        Args:
            string (str):  string to search.

        Returns:
            tuple: True/False and PypeVersion if found.

        """
        try:
            result = PypeVersion._decompose_version(string)
        except ValueError:
            return False, None
        return True, PypeVersion(major=result[0],
                                 minor=result[1],
                                 subversion=result[2],
                                 variant=result[3],
                                 client=result[4])


class BootstrapRepos:
    """Class for bootstrapping local Pype installation.

    Attributes:
        data_dir (Path): local Pype installation directory.
        live_repo_dir (Path): path to repos directory if running live,
            otherwise `None`.
        registry (PypeSettingsRegistry): Pype registry object.
        zip_filter (list): List of files to exclude from zip
        pype_filter (list): list of top level directories not to include in
            zip in Pype repository.

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
        self._app = "pype"
        self._log = log.getLogger(str(__class__))
        self.data_dir = Path(user_data_dir(self._app, self._vendor))
        self.registry = PypeSettingsRegistry()
        self.zip_filter = [".pyc", "__pycache__"]
        self.pype_filter = [
            "build", "docs", "tests", "repos", "tools", "venv"
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
        """Get path for specific version in list of Pype versions.

        Args:
            version (str): Version string to look for (1.2.4-staging)
            version_list (list of PypeVersion): list of version to search.

        Returns:
            Path: Path to given version.

        """
        for v in version_list:
            if str(v) == version:
                return v.path

    @staticmethod
    def get_local_live_version() -> str:
        """Get version of local Pype."""

        version = {}
        path = Path(os.path.dirname(__file__)).parent / "pype" / "version.py"
        with open(path, "r") as fp:
            exec(fp.read(), version)
        return version["__version__"]

    @staticmethod
    def get_version(repo_dir: Path) -> Union[str, None]:
        """Get version of Pype in given directory.

        Note: in frozen Pype installed in user data dir, this must point
        one level deeper as it is `pype-version-v3.0.0/pype/pype/version.py`

        Args:
            repo_dir (Path): Path to Pype repo.

        Returns:
            str: version string.
            None: if Pype is not found.

        """
        # try to find version
        version_file = Path(repo_dir) / "pype" / "version.py"
        if not version_file.exists():
            return None

        version = {}
        with version_file.open("r") as fp:
            exec(fp.read(), version)

        return version['__version__']

    def create_version_from_live_code(
            self, repo_dir: Path = None) -> Union[PypeVersion, None]:
        """Copy zip created from Pype repositories to user data dir.

        This detect Pype version either in local "live" Pype repository
        or in user provided path. Then it will zip it in temporary directory
        and finally it will move it to destination which is user data
        directory. Existing files will be replaced.

        Args:
            repo_dir (Path, optional): Path to Pype repository.

        Returns:
            Path: path of installed repository file.

        """
        # if repo dir is not set, we detect local "live" Pype repository
        # version and use it as a source. Otherwise repo_dir is user
        # entered location.
        if not repo_dir:
            version = self.get_local_live_version()
            repo_dir = self.live_repo_dir
        else:
            version = self.get_version(repo_dir)

        if not version:
            self._print("Pype not found.", LOG_ERROR)
            return

        # create destination directory
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)

        # create zip inside temporary directory.
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = \
                Path(temp_dir) / f"pype-v{version}.zip"
            self._print(f"creating zip: {temp_zip}")

            self._create_pype_zip(temp_zip, repo_dir)
            if not os.path.exists(temp_zip):
                self._print("make archive failed.", LOG_ERROR)
                return None

            destination = self._move_zip_to_data_dir(temp_zip)

        return PypeVersion(version=version, path=destination)

    def _move_zip_to_data_dir(self, zip_file) -> Union[None, Path]:
        """Move zip with Pype version to user data directory.

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

    def create_version_from_frozen_code(self) -> Union[None, PypeVersion]:
        """Create Pype version from *frozen* code distributed by installer.

        This should be real edge case for those wanting to try out Pype
        without setting up whole infrastructure but is strongly discouraged
        in studio setup as this use local version independent of others
        that can be out of date.

        Returns:
            :class:`PypeVersion` zip file to be installed.

        """
        frozen_root = Path(sys.executable).parent
        repo_dir = frozen_root / "repos"
        repo_list = self._filter_dir(
            repo_dir, self.zip_filter)

        # from frozen code we need igniter, pype, schema vendor
        pype_list = self._filter_dir(
            frozen_root / "pype", self.zip_filter)
        pype_list += self._filter_dir(
            frozen_root / "igniter", self.zip_filter)
        pype_list += self._filter_dir(
            frozen_root / "schema", self.zip_filter)
        pype_list += self._filter_dir(
            frozen_root / "vendor", self.zip_filter)
        pype_list.append(frozen_root / "README.md")
        pype_list.append(frozen_root / "LICENSE")

        version = self.get_version(frozen_root)

        # create zip inside temporary directory.
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = \
                Path(temp_dir) / f"pype-v{version}.zip"
            self._print(f"creating zip: {temp_zip}")

            with ZipFile(temp_zip, "w") as zip_file:
                progress = 0
                repo_inc = 48.0 / float(len(repo_list))
                file: Path
                for file in repo_list:
                    progress += repo_inc
                    self._progress_callback(int(progress))

                    # archive name is relative to repos dir
                    arc_name = file.relative_to(repo_dir)
                    zip_file.write(file, arc_name)

                pype_inc = 48.0 / float(len(pype_list))
                file: Path
                for file in pype_list:
                    progress += pype_inc
                    self._progress_callback(int(progress))

                    arc_name = file.relative_to(frozen_root.parent)
                    # we need to replace first part of path which starts with
                    # something like `exe.win/linux....` with `pype` as this
                    # is expected by Pype in zip archive.
                    arc_name = Path("pype").joinpath(*arc_name.parts[1:])
                    zip_file.write(file, arc_name)

            destination = self._move_zip_to_data_dir(temp_zip)

        return PypeVersion(version=version, path=destination)

    def _create_pype_zip(
            self,
            zip_path: Path, include_dir: Path,
            include_pype: bool = True) -> None:
        """Pack repositories and Pype into zip.

        We are using :mod:`zipfile` instead :meth:`shutil.make_archive`
        because we need to decide what file and directories to include in zip
        and what not. They are determined by :attr:`zip_filter` on file level
        and :attr:`pype_filter` on top level directory in Pype repository.

        Args:
            zip_path (str): path  to zip file.
            include_dir (Path): repo directories to include.
            include_pype (bool): add Pype module itself.

        """
        include_dir = include_dir.resolve()

        pype_list = []
        # get filtered list of files in repositories (repos directory)
        repo_list = self._filter_dir(include_dir, self.zip_filter)
        # count them
        repo_files = len(repo_list)

        # there must be some files, otherwise `include_dir` path is wrong
        assert repo_files != 0, f"No repositories to include in {include_dir}"
        pype_inc = 0
        if include_pype:
            # get filtered list of file in Pype repository
            pype_list = self._filter_dir(include_dir.parent, self.zip_filter)
            pype_files = len(pype_list)
            repo_inc = 48.0 / float(repo_files)
            pype_inc = 48.0 / float(pype_files)
        else:
            repo_inc = 98.0 / float(repo_files)

        with ZipFile(zip_path, "w") as zip_file:
            progress = 0
            file: Path
            for file in repo_list:
                progress += repo_inc
                self._progress_callback(int(progress))

                # archive name is relative to repos dir
                arc_name = file.relative_to(include_dir)
                zip_file.write(file, arc_name)

            # add pype itself
            if include_pype:
                pype_root = include_dir.parent.resolve()
                # generate list of filtered paths
                dir_filter = [pype_root / f for f in self.pype_filter]

                file: Path
                for file in pype_list:
                    progress += pype_inc
                    self._progress_callback(int(progress))

                    # if file resides in filtered path, skip it
                    is_inside = None
                    df: Path
                    for df in dir_filter:
                        try:
                            is_inside = file.resolve().relative_to(df)
                        except ValueError:
                            pass

                    if is_inside:
                        continue

                    processed_path = file
                    self._print(f"- processing {processed_path}")

                    zip_file.write(file,
                                   "pype" / file.relative_to(pype_root))

            # test if zip is ok
            zip_file.testzip()
            self._progress_callback(100)

    @staticmethod
    def add_paths_from_archive(archive: Path) -> None:
        """Add first-level directories as paths to :mod:`sys.path`.

        This will enable Python to import modules is second-level directories
        in zip file.

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
        for item in name_list:
            root = item.split("/")[0]
            if root not in roots:
                roots.append(root)
                sys.path.insert(0, f"{archive}{os.path.sep}{root}")

        pythonpath = os.getenv("PYTHONPATH", "")
        paths = pythonpath.split(os.pathsep)
        paths += roots

        os.environ["PYTHONPATH"] = os.pathsep.join(paths)

    @staticmethod
    def add_paths_from_directory(directory: Path) -> None:
        """Add first level directories as paths to :mod:`sys.path`.

        This works the same as :meth:`add_paths_from_archive` but in
        specified directory.

        Adding to both `sys.path` and `PYTHONPATH`, skipping duplicates.

        Args:
            directory (Path): path to directory.

        """
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

    def find_pype(
            self,
            pype_path: Union[Path, str] = None,
            staging: bool = False,
            include_zips: bool = False) -> Union[List[PypeVersion], None]:
        """Get ordered dict of detected Pype version.

        Resolution order for Pype is following:

            1) First we test for ``OPENPYPE_PATH`` environment variable
            2) We try to find ``pypePath`` in registry setting
            3) We use user data directory

        Args:
            pype_path (Path or str, optional): Try to find Pype on the given
                path or url.
            staging (bool, optional): Filter only staging version, skip them
                otherwise.
            include_zips (bool, optional): If set True it will try to find
                Pype in zip files in given directory.

        Returns:
            dict of Path: Dictionary of detected Pype version.
                 Key is version, value is path to zip file.

            None: if Pype is not found.

        Todo:
            implement git/url support as Pype location, so it would be
            possible to enter git url, Pype would check it out and if it is
            ok install it as normal version.

        """
        if pype_path and not isinstance(pype_path, Path):
            raise NotImplementedError(
                ("Finding Pype in non-filesystem locations is"
                 " not implemented yet."))

        dir_to_search = self.data_dir

        # if we have pype_path specified, search only there.
        if pype_path:
            dir_to_search = pype_path
        else:
            if os.getenv("OPENPYPE_PATH"):
                if Path(os.getenv("OPENPYPE_PATH")).exists():
                    dir_to_search = Path(os.getenv("OPENPYPE_PATH"))
            else:
                try:
                    registry_dir = Path(
                        str(self.registry.get_item("pypePath")))
                    if registry_dir.exists():
                        dir_to_search = registry_dir

                except ValueError:
                    # nothing found in registry, we'll use data dir
                    pass

        pype_versions = self.get_pype_versions(dir_to_search, staging)

        # remove zip file version if needed.
        if not include_zips:
            pype_versions = [
                v for v in pype_versions if v.path.suffix != ".zip"
            ]

        return pype_versions

    def process_entered_location(self, location: str) -> Union[Path, None]:
        """Process user entered location string.

        It decides if location string is mongodb url or path.
        If it is mongodb url, it will connect and load ``OPENPYPE_PATH`` from
        there and use it as path to Pype. In it is _not_ mongodb url, it
        is assumed we have a path, this is tested and zip file is
        produced and installed using :meth:`create_version_from_live_code`.

        Args:
            location (str): User entered location.

        Returns:
            Path: to Pype zip produced from this location.
            None: Zipping failed.

        """
        pype_path = None
        # try to get pype path from mongo.
        if location.startswith("mongodb"):
            pype_path = get_pype_path_from_db(location)
            if not pype_path:
                self._print("cannot find OPENPYPE_PATH in settings.")
                return None

        # if not successful, consider location to be fs path.
        if not pype_path:
            pype_path = Path(location)

        # test if this path does exist.
        if not pype_path.exists():
            self._print(f"{pype_path} doesn't exists.")
            return None

        # test if entered path isn't user data dir
        if self.data_dir == pype_path:
            self._print("cannot point to user data dir", LOG_ERROR)
            return None

        # find pype zip files in location. There can be
        # either "live" Pype repository, or multiple zip files or even
        # multiple pype version directories. This process looks into zip
        # files and directories and tries to parse `version.py` file.
        versions = self.find_pype(pype_path, include_zips=True)
        if versions:
            self._print(f"found Pype in [ {pype_path} ]")
            self._print(f"latest version found is [ {versions[-1]} ]")

            return self.install_version(versions[-1])

        # if we got here, it means that location is "live" Pype repository.
        # we'll create zip from it and move it to user data dir.
        live_pype = self.create_version_from_live_code(pype_path)
        if not live_pype.path.exists():
            self._print(f"installing zip {live_pype} failed.", LOG_ERROR)
            return None
        # install it
        return self.install_version(live_pype)

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

    def extract_pype(self, version: PypeVersion) -> Union[Path, None]:
        """Extract zipped Pype version to user data directory.

        Args:
            version (PypeVersion): Version of Pype.

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
            # if relative path cannot be calculated, Pype version is not
            # inside user data dir
            pass
        return is_inside

    def install_version(self,
                        pype_version: PypeVersion,
                        force: bool = False) -> Path:
        """Install Pype version to user data directory.

        Args:
            pype_version (PypeVersion): Pype version to install.
            force (bool, optional): Force overwrite existing version.

        Returns:
            Path: Path to installed Pype.

        Raises:
            PypeVersionExists: If not forced and this version already exist
                in user data directory.
            PypeVersionInvalid: If version to install is invalid.
            PypeVersionIOError: If copying or zipping fail.

        """

        if self.is_inside_user_data(pype_version.path) and not pype_version.path.is_file():  # noqa
            raise PypeVersionExists("Pype already inside user data dir")

        # determine destination directory name
        # for zip file strip suffix, in case of dir use whole dir name
        if pype_version.path.is_dir():
            dir_name = pype_version.path.name
        else:
            dir_name = pype_version.path.stem

        destination = self.data_dir / dir_name

        # test if destination directory already exist, if so lets delete it.
        if destination.exists() and force:
            try:
                shutil.rmtree(destination)
            except OSError as e:
                self._print(
                    f"cannot remove already existing {destination}",
                    LOG_ERROR, exc_info=True)
                raise PypeVersionIOError(
                    f"cannot remove existing {destination}") from e
        elif destination.exists() and not force:
            raise PypeVersionExists(f"{destination} already exist.")
        else:
            # create destination parent directories even if they don't exist.
            destination.mkdir(parents=True)

        # version is directory
        if pype_version.path.is_dir():
            # create zip inside temporary directory.
            self._print("Creating zip from directory ...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_zip = \
                    Path(temp_dir) / f"pype-v{pype_version}.zip"
                self._print(f"creating zip: {temp_zip}")

                self._create_pype_zip(temp_zip, pype_version.path)
                if not os.path.exists(temp_zip):
                    self._print("make archive failed.", LOG_ERROR)
                    raise PypeVersionIOError("Zip creation failed.")

                # set zip as version source
                pype_version.path = temp_zip

        elif pype_version.path.is_file():
            # check if file is zip (by extension)
            if pype_version.path.suffix.lower() != ".zip":
                raise PypeVersionInvalid("Invalid file format")

        if not self.is_inside_user_data(pype_version.path):
            try:
                # copy file to destination
                self._print("Copying zip to destination ...")
                _destination_zip = destination.parent / pype_version.path.name
                copyfile(
                    pype_version.path.as_posix(),
                    _destination_zip.as_posix())
            except OSError as e:
                self._print(
                    "cannot copy version to user data directory", LOG_ERROR,
                    exc_info=True)
                raise PypeVersionIOError((
                    f"can't copy version {pype_version.path.as_posix()} "
                    f"to destination {destination.parent.as_posix()}")) from e

        # extract zip there
        self._print("extracting zip to destination ...")
        with ZipFile(pype_version.path, "r") as zip_ref:
            zip_ref.extractall(destination)

        return destination

    def _is_pype_in_dir(self,
                        dir_item: Path,
                        detected_version: PypeVersion) -> bool:
        """Test if path item is Pype version matching detected version.

        If item is directory that might (based on it's name)
        contain Pype version, check if it really does contain
        Pype and that their versions matches.

        Args:
            dir_item (Path): Directory to test.
            detected_version (PypeVersion): Pype version detected from name.

        Returns:
            True if it is valid Pype version, False otherwise.

        """
        try:
            # add one 'pype' level as inside dir there should
            # be many other repositories.
            version_str = BootstrapRepos.get_version(
                dir_item / "pype")
            version_check = PypeVersion(version=version_str)
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

    def _is_pype_in_zip(self,
                        zip_item: Path,
                        detected_version: PypeVersion) -> bool:
        """Test if zip path is Pype version matching detected version.

        Open zip file, look inside and parse version from Pype
        inside it. If there is none, or it is different from
        version specified in file name, skip it.

        Args:
            zip_item (Path): Zip file to test.
            detected_version (PypeVersion): Pype version detected from name.

        Returns:
           True if it is valid Pype version, False otherwise.

        """
        # skip non-zip files
        if zip_item.suffix.lower() != ".zip":
            return False

        try:
            with ZipFile(zip_item, "r") as zip_file:
                with zip_file.open(
                        "pype/pype/version.py") as version_file:
                    zip_version = {}
                    exec(version_file.read(), zip_version)
                    version_check = PypeVersion(
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
            self._print("Zip does not contain Pype", True)
            return False
        return True

    def get_pype_versions(self, pype_dir: Path, staging: bool = False) -> list:
        """Get all detected Pype versions in directory.

        Args:
            pype_dir (Path): Directory to scan.
            staging (bool, optional): Find staging versions if True.

        Returns:
            list of PypeVersion

        Throws:
            ValueError: if invalid path is specified.

        """
        if not pype_dir.exists() and not pype_dir.is_dir():
            raise ValueError("specified directory is invalid")

        _pype_versions = []
        # iterate over directory in first level and find all that might
        # contain Pype.
        for item in pype_dir.iterdir():

            # if file, strip extension, in case of dir not.
            name = item.name if item.is_dir() else item.stem
            result = PypeVersion.version_in_str(name)

            if result[0]:
                detected_version: PypeVersion
                detected_version = result[1]

                if item.is_dir() and not self._is_pype_in_dir(
                    item, detected_version
                ):
                    continue

                if item.is_file() and not self._is_pype_in_zip(
                    item, detected_version
                ):
                    continue

                detected_version.path = item
                if staging and detected_version.is_staging():
                    _pype_versions.append(detected_version)

                if not staging and not detected_version.is_staging():
                    _pype_versions.append(detected_version)

        return sorted(_pype_versions)


class PypeVersionExists(Exception):
    """Exception for handling existing Pype version."""
    pass


class PypeVersionInvalid(Exception):
    """Exception for handling invalid Pype version."""
    pass


class PypeVersionIOError(Exception):
    """Exception for handling IO errors in Pype version."""
    pass
