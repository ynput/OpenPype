# -*- coding: utf-8 -*-
"""Bootstrap Pype repositories.

Attrbutes:
    data_dir (str): platform dependent path where pype expects its
        repositories and configuration files.
"""
import sys
import os
import logging as log
import shutil
import tempfile
from typing import Union, Callable
from zipfile import ZipFile

from appdirs import user_data_dir
from version import __version__


class BootstrapRepos():
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
            self.live_repo_dir = None
        else:
            self.live_repo_dir = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "repos"
                )
            )

    def get_local_version(self) -> str:
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
            # shutil.make_archive(temp_zip, "zip", repo_dir)
            self._create_pype_zip(
                temp_zip, repo_dir, progress_callback=progress_callback)
            if not os.path.exists(temp_zip):
                self._log.error("make archive failed.")
                return None
            shutil.move(temp_zip, self.data_dir)
        return os.path.join(self.data_dir, os.path.basename(temp_zip))

    def _create_pype_zip(
            self, zip_path: str, dir: str,
            progress_callback: Callable, include_pype: bool = True) -> None:
        """Pack repositories and Pype into zip.

        We are using `zipfile` instead :meth:`shutil.make_archive()` to later
        implement file filter to skip git related stuff to make it into
        archive.

        Todo:
            Implement file filter

        Args:
            zip_path (str): path  to zip file.
            dir: repo directories to inlcude.
            progress_callback (Callable): callback to report progress back to
                UI progress bar.
            include_pype (bool): add Pype module itelf.
        """
        repo_files = sum(len(files) for _, _, files in os.walk(dir))
        if include_pype:
            pype_files = sum(len(files) for _, _, files in os.walk('pype'))
            repo_inc = 48.0 / float(repo_files)
            pype_inc = 48.0 / float(pype_files)
        else:
            repo_inc = 98.0 / float(repo_files)
        progress = 0
        with ZipFile(zip_path, "w") as zip:
            for root, _, files in os.walk(dir):
                for file in files:
                    zip.write(
                        os.path.relpath(os.path.join(root, file),
                                        os.path.join(dir, '..')),
                        os.path.relpath(os.path.join(root, file),
                                        os.path.join(dir))
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

    def add_paths_from_archive(self, archive: str) -> None:
        """Add first-level directories as paths to sys.path.

        This will enable Python to import modules is second-level directories
        in zip file.

        Args:
            archive (str): path to archive.

        """
        pass
