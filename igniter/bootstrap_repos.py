# -*- coding: utf-8 -*-
"""Bootstrap Pype repositories."""
import sys
import os
import re
import logging as log
import shutil
import tempfile
from typing import Union, Callable, Dict
from zipfile import ZipFile
from pathlib import Path

from appdirs import user_data_dir
from pype.version import __version__
from pype.lib import PypeSettingsRegistry
from .tools import load_environments


class BootstrapRepos:
    """Class for bootstrapping local Pype installation.

    Attributes:
        data_dir (Path): local Pype installation directory.
        live_repo_dir (Path): path to repos directory if running live,
            otherwise `None`.

    """

    def __init__(self, progress_callback: Callable = None):
        """Constructor.

        Args:
            progress_callback (callable): Optional callback method to report
                progress.

        """
        # vendor and app used to construct user data dir
        self._vendor = "pypeclub"
        self._app = "pype"
        self._log = log.getLogger(str(__class__))
        self.data_dir = Path(user_data_dir(self._app, self._vendor))
        self.registry = PypeSettingsRegistry()

        # dummy progress reporter
        def empty_progress(x: int):
            return x

        if not progress_callback:
            progress_callback = empty_progress
        self._progress_callback = progress_callback

        if getattr(sys, "frozen", False):
            self.live_repo_dir = Path(sys.executable).parent / "repos"
        else:
            self.live_repo_dir = Path(Path(__file__).parent / ".." / "repos")

    @staticmethod
    def get_local_version() -> str:
        """Get version of local Pype."""
        return __version__

    @staticmethod
    def get_version(repo_dir: Path) -> Union[str, None]:
        """Get version of Pype in given directory.

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

    def install_live_repos(self, repo_dir: Path = None) -> Union[Path, None]:
        """Copy zip created from Pype repositories to user data dir.

        Args:
            repo_dir (Path, optional): Path to Pype repository.

        Returns:
            Path: path of installed repository file.

        """
        if not repo_dir:
            version = self.get_local_version()
            repo_dir = self.live_repo_dir
        else:
            version = self.get_version(repo_dir)

        # create destination directory
        try:
            os.makedirs(self.data_dir)
        except OSError:
            self._log.error("directory already exists")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = \
                Path(temp_dir) / f"pype-repositories-v{version}.zip"
            self._log.info(f"creating zip: {temp_zip}")

            self._create_pype_zip(temp_zip, repo_dir)
            if not os.path.exists(temp_zip):
                self._log.error("make archive failed.")
                return None

            destination = self.data_dir / temp_zip.name

            if destination.exists():
                self._log.warning(
                    f"Destination file {destination} exists, removing.")
                try:
                    destination.unlink()
                except Exception as e:
                    self._log.error(e)
                    return None
            try:
                shutil.move(temp_zip.as_posix(), self.data_dir.as_posix())
            except shutil.Error as e:
                self._log.error(e)
                return None
        return self.data_dir / temp_zip.name

    def _create_pype_zip(
            self,
            zip_path: Path, include_dir: Path,
            include_pype: bool = True) -> None:
        """Pack repositories and Pype into zip.

        We are using :mod:`zipfile` instead :meth:`shutil.make_archive`
        to later implement file filter to skip git related stuff to make
        it into archive.

        Todo:
            Implement file filter

        Args:
            zip_path (str): path  to zip file.
            include_dir (Path): repo directories to include.
            include_pype (bool): add Pype module itself.

        """
        repo_files = sum(len(files) for _, _, files in os.walk(include_dir))
        assert repo_files != 0, f"No repositories to include in {include_dir}"
        pype_inc = 0
        if include_pype:
            pype_files = sum(len(files) for _, _, files in os.walk('pype'))
            repo_inc = 48.0 / float(repo_files)
            pype_inc = 48.0 / float(pype_files)
        else:
            repo_inc = 98.0 / float(repo_files)
        progress = 0
        with ZipFile(zip_path, "w") as zip_file:
            for root, _, files in os.walk(include_dir.as_posix()):
                for file in files:
                    zip_file.write(
                        os.path.relpath(os.path.join(root, file),
                                        os.path.join(include_dir, '..')),
                        os.path.relpath(os.path.join(root, file),
                                        os.path.join(include_dir))
                    )
                    progress += repo_inc
                    self._progress_callback(int(progress))
            # add pype itself
            if include_pype:
                for root, _, files in os.walk("pype"):
                    for file in files:
                        zip_file.write(
                            os.path.relpath(os.path.join(root, file),
                                            os.path.join('pype', '..')),
                            os.path.join(
                                'pype',
                                os.path.relpath(os.path.join(root, file),
                                                os.path.join('pype', '..')))
                        )
                        progress += pype_inc
                        self._progress_callback(int(progress))
            zip_file.testzip()
            self._progress_callback(100)

    @staticmethod
    def add_paths_from_archive(archive: Path) -> None:
        """Add first-level directories as paths to :mod:`sys.path`.

        This will enable Python to import modules is second-level directories
        in zip file.

        Args:
            archive (str): path to archive.

        """
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

    def find_pype(self) -> Union[Dict[str, Path], None]:
        """Get ordered dict of detected Pype version.

        Resolution order for Pype is following:

            1) First we test for ``PYPE_PATH`` environment variable
            2) We try to find ``pypePath`` in registry setting
            3) We use user data directory

        Returns:
            dict of Path: Dictionary of detected Pype version.
                 Key is version, value is path to zip file.

            None: if Pype is not found.

        """
        dir_to_search = self.data_dir
        if os.getenv("PYPE_PATH"):
            if Path(os.getenv("PYPE_PATH")).exists():
                dir_to_search = Path(os.getenv("PYPE_PATH"))
        else:
            try:
                registry_dir = Path(self.registry.get_item("pypePath"))
                if registry_dir.exists():
                    dir_to_search = registry_dir

            except ValueError:
                # nothing found in registry, we'll use data dir
                pass

        # pype installation dir doesn't exists
        if not dir_to_search.exists():
            return None

        _pype_versions = {}
        for file in dir_to_search.iterdir():
            m = re.match(
                r"^pype-repositories-v(?P<version>\d+\.\d+\.\d+).zip$",
                file.name)
            if m:
                _pype_versions[m.group("version")] = file

        return dict(sorted(_pype_versions.items()))

    @staticmethod
    def _get_pype_from_mongo(mongo_url: str) -> Union[Path, None]:
        """Get path from Mongo database.

        This sets environment variable ``AVALON_MONGO`` for
        :mod:`pype.settings` to be able to read data from database.
        It will then retrieve environment variables and among them
        must be ``PYPE_ROOT``.

        Args:
            mongo_url (str): mongodb connection url

        Returns:
            Path: if path from ``PYPE_ROOT`` is found.
            None: if not.

        """
        os.environ["AVALON_MONGO"] = mongo_url
        env = load_environments()
        if not env.get("PYPE_PATH"):
            return None
        return Path(env.get("PYPE_PATH"))

    def process_entered_location(self, location: str) -> Union[Path, None]:
        """Process user entered location string.

        It decides if location string is mongodb url or path.
        If it is mongodb url, it will connect and load ``PYPE_PATH`` from
        there and use it as path to Pype. In it is _not_ mongodb url, it
        is assumed we have a path, this is tested and zip file is
        produced and installed using :meth:`install_live_repos`.

        Args:
            location (str): User entered location.

        Returns:
            Path: to Pype zip produced from this location.
            None: Zipping failed.

        """
        pype_path = None
        if location.startswith("mongodb"):
            pype_path = self._get_pype_from_mongo(location)
            if not pype_path:
                self._log.error("cannot find PYPE_PATH in settings.")
                return None

        if not pype_path:
            pype_path = Path(location)

        if not pype_path.exists():
            self._log.error(f"{pype_path} doesn't exists.")
            return None

        repo_file = self.install_live_repos(pype_path)
        if not repo_file.exists():
            self._log.error(f"installing zip {repo_file} failed.")
            return None
        return repo_file
