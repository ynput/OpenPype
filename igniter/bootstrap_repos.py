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

from appdirs import user_data_dir
from pype.version import __version__


class BootstrapRepos:
    """Class for bootstrapping local Pype installation.

    Attributes:
        data_dir (str): local Pype installation directory.
        live_repo_dir (str): path to repos directory if running live,
            otherwise `None`.
    """
    _vendor = "pypeclub"
    _app = "pype"

    def __init__(self):
        self._log = log.getLogger(str(__class__))
        self.data_dir = user_data_dir(self._app, self._vendor)
        if getattr(sys, 'frozen', False):
            self.live_repo_dir = os.path.join(
                os.path.dirname(sys.executable),
                "repos"
            )
        else:
            self.live_repo_dir = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "repos"
                )
            )

    @staticmethod
    def get_local_version() -> str:
        """Get version of local Pype."""
        return __version__

    def install_live_repos(self, progress_callback=None) -> Union[str, None]:
        """Copy zip created from local repositories to user data dir.

        Args:
            progress_callback (callable): Optional callback method to report
                progress.
        Returns:
            str: path of installed repository file.
        """
        # dummy progress reporter
        def empty_progress(x: int):
            return x

        if not progress_callback:
            progress_callback = empty_progress

        # create zip from repositories
        local_version = self.get_local_version()
        repo_dir = self.live_repo_dir

        # create destination directory
        try:
            os.makedirs(self.data_dir)
        except OSError:
            self._log.error("directory already exists")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = os.path.join(
                temp_dir,
                f"pype-repositories-v{local_version}.zip"
            )
            self._log.info(f"creating zip: {temp_zip}")

            BootstrapRepos._create_pype_zip(
                temp_zip, repo_dir, progress_callback=progress_callback)
            if not os.path.exists(temp_zip):
                self._log.error("make archive failed.")
                return None

            destination = os.path.join(
                self.data_dir, os.path.basename(temp_zip))

            if os.path.exists(destination):
                self._log.warning(
                    f"Destination file {destination} exists, removing.")
                try:
                    os.remove(destination)
                except Exception as e:
                    self._log.error(e)
                    return None
            try:
                shutil.move(temp_zip, self.data_dir)
            except shutil.Error as e:
                self._log.error(e)
                return None
        return os.path.join(self.data_dir, os.path.basename(temp_zip))

    @staticmethod
    def _create_pype_zip(
            zip_path: str, include_dir: str,
            progress_callback: Callable, include_pype: bool = True) -> None:
        """Pack repositories and Pype into zip.

        We are using `zipfile` instead :meth:`shutil.make_archive` to later
        implement file filter to skip git related stuff to make it into
        archive.

        Todo:
            Implement file filter

        Args:
            zip_path (str): path  to zip file.
            include_dir: repo directories to include.
            progress_callback (Callable): callback to report progress back to
                UI progress bar.
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
        with ZipFile(zip_path, "w") as zip:
            for root, _, files in os.walk(include_dir):
                for file in files:
                    zip.write(
                        os.path.relpath(os.path.join(root, file),
                                        os.path.join(include_dir, '..')),
                        os.path.relpath(os.path.join(root, file),
                                        os.path.join(include_dir))
                    )
                    progress += repo_inc
                    progress_callback(int(progress))
            # add pype itself
            if include_pype:
                for root, _, files in os.walk("pype"):
                    for file in files:
                        zip.write(
                            os.path.relpath(os.path.join(root, file),
                                            os.path.join('pype', '..')),
                            os.path.join(
                                'pype',
                                os.path.relpath(os.path.join(root, file),
                                                os.path.join('pype', '..')))
                        )
                        progress += pype_inc
                        progress_callback(int(progress))
            zip.testzip()
            progress_callback(100)

    @staticmethod
    def add_paths_from_archive(archive: str) -> None:
        """Add first-level directories as paths to sys.path.

        This will enable Python to import modules is second-level directories
        in zip file.

        Args:
            archive (str): path to archive.

        """
        name_list = []
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

    def find_pype(self) -> Union[Dict, None]:
        """Get ordered dict of detected Pype version.

        Returns:
            dict: Dictionary of detected Pype version. Key is version, value
                is path to zip file.
            None: if Pype is not found.
        """
        # pype installation dir doesn't exists
        if not os.path.exists(self.data_dir):
            return None

        # f"pype-repositories-v{local_version}.zip"
        files = os.listdir(self.data_dir)
        _pype_versions = {}
        for file in files:
            m = re.match(
                r"^pype-repositories-v(?P<version>\d+\.\d+\.\d+).zip$", file)
            if m:
                _pype_versions[m.group("version")] = os.path.join(
                    self.data_dir, file)

        return dict(sorted(_pype_versions.items()))
