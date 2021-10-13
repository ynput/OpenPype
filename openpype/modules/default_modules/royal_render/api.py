# -*- coding: utf-8 -*-
"""Wrapper around Royal Render API."""
import sys
import os

from openpype.settings import get_project_settings
from openpype.lib.local_settings import OpenPypeSettingsRegistry
from openpype.lib import PypeLogger, run_subprocess
from .rr_job import RRJob, SubmitFile, SubmitterParameter


log = PypeLogger.get_logger("RoyalRender")


class Api:

    _settings = None
    RR_SUBMIT_CONSOLE = 1
    RR_SUBMIT_API = 2

    def __init__(self, settings, project=None):
        self._settings = settings
        self._initialize_rr(project)

    def _initialize_rr(self, project=None):
        # type: (str) -> None
        """Initialize RR Path.

        Args:
            project (str, Optional): Project name to set RR api in
                context.

        """
        if project:
            project_settings = get_project_settings(project)
            rr_path = (
                project_settings
                ["royalrender"]
                ["rr_paths"]
            )
        else:
            rr_path = (
                self._settings
                ["modules"]
                ["royalrender"]
                ["rr_path"]
                ["default"]
            )
        os.environ["RR_ROOT"] = rr_path
        self._rr_path = rr_path

    def _get_rr_bin_path(self, rr_root=None):
        # type: (str) -> str
        """Get path to RR bin folder."""
        rr_root = rr_root or self._rr_path
        is_64bit_python = sys.maxsize > 2 ** 32

        rr_bin_path = ""
        if sys.platform.lower() == "win32":
            rr_bin_path = "/bin/win64"
            if not is_64bit_python:
                # we are using 64bit python
                rr_bin_path = "/bin/win"
            rr_bin_path = rr_bin_path.replace(
                "/", os.path.sep
            )

        if sys.platform.lower() == "darwin":
            rr_bin_path = "/bin/mac64"
            if not is_64bit_python:
                rr_bin_path = "/bin/mac"

        if sys.platform.lower() == "linux":
            rr_bin_path = "/bin/lx64"

        return os.path.join(rr_root, rr_bin_path)

    def _initialize_module_path(self):
        # type: () -> None
        """Set RR modules for Python."""
        # default for linux
        rr_bin = self._get_rr_bin_path()
        rr_module_path = os.path.join(rr_bin, "lx64/lib")

        if sys.platform.lower() == "win32":
            rr_module_path = rr_bin
            rr_module_path = rr_module_path.replace(
                "/", os.path.sep
            )

        if sys.platform.lower() == "darwin":
            rr_module_path = os.path.join(rr_bin, "lib/python/27")

        sys.path.append(os.path.join(self._rr_path, rr_module_path))

    def create_submission(self, jobs, submitter_attributes, file_name=None):
        # type: (list[RRJob], list[SubmitterParameter], str) -> SubmitFile
        """Create jobs submission file.

        Args:
            jobs (list): List of :class:`RRJob`
            submitter_attributes (list): List of submitter attributes
                :class:`SubmitterParameter` for whole submission batch.
            file_name (str), optional): File path to write data to.

        Returns:
            str: XML data of job submission files.

        """
        raise NotImplementedError

    def submit_file(self, file, mode=RR_SUBMIT_CONSOLE):
        # type: (SubmitFile, int) -> None
        if mode == self.RR_SUBMIT_CONSOLE:
            self._submit_using_console(file)

        # RR v7 supports only Python 2.7 so we bail out in fear
        # until there is support for Python 3 😰
        raise NotImplementedError(
            "Submission via RoyalRender API is not supported yet")
        # self._submit_using_api(file)

    def _submit_using_console(self, file):
        # type: (SubmitFile) -> bool
        rr_console = os.path.join(
            self._get_rr_bin_path(),
            "rrSubmitterconsole"
        )

        if sys.platform.lower() == "darwin":
            if "/bin/mac64" in rr_console:
                rr_console = rr_console.replace("/bin/mac64", "/bin/mac")

        if sys.platform.lower() == "win32":
            if "/bin/win64" in rr_console:
                rr_console = rr_console.replace("/bin/win64", "/bin/win")
            rr_console += ".exe"

        args = [rr_console, file]
        run_subprocess(" ".join(args), logger=log)

    def _submit_using_api(self, file):
        # type: (SubmitFile) -> None
        """Use RR API to submit jobs.

        Args:
            file (SubmitFile): Submit jobs definition.

        Throws:
            RoyalRenderException: When something fails.

        """
        self._initialize_module_path()
        import libpyRR2 as rrLib  # noqa
        from rrJob import getClass_JobBasics  # noqa
        import libpyRR2 as _RenderAppBasic  # noqa

        tcp = rrLib._rrTCP("")  # noqa
        rr_server = tcp.getRRServer()

        if len(rr_server) == 0:
            log.info("Got RR IP address {}".format(rr_server))

        # TODO: Port is hardcoded in RR? If not, move it to Settings
        if not tcp.setServer(rr_server, 7773):
            log.error(
                "Can not set RR server: {}".format(tcp.errorMessage()))
            raise RoyalRenderException(tcp.errorMessage())

        # TODO: This need UI and better handling of username/password.
        # We can't store password in keychain as it is pulled multiple
        # times and users on linux must enter keychain password every time.
        # Probably best way until we setup our own user management would be
        # to encrypt password and save it to json locally. Not bulletproof
        # but at least it is not stored in plaintext.
        reg = OpenPypeSettingsRegistry()
        try:
            rr_user = reg.get_item("rr_username")
            rr_password = reg.get_item("rr_password")
        except ValueError:
            # user has no rr credentials set
            pass
        else:
            # login to RR
            tcp.setLogin(rr_user, rr_password)

        job = getClass_JobBasics()
        renderer = _RenderAppBasic()

        # iterate over SubmitFile, set _JobBasic (job) and renderer
        # and feed it to jobSubmitNew()
        # not implemented yet
        job.renderer = renderer
        tcp.jobSubmitNew(job)


class RoyalRenderException(Exception):
    """Exception used in various error states coming from RR."""
    pass
