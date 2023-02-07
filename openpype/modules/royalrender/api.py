# -*- coding: utf-8 -*-
"""Wrapper around Royal Render API."""
import sys
import os

from openpype.lib.local_settings import OpenPypeSettingsRegistry
from openpype.lib import Logger, run_subprocess
from .rr_job import RRJob, SubmitFile, SubmitterParameter
from openpype.lib.vendor_bin_utils import find_tool_in_custom_paths


class Api:

    _settings = None
    RR_SUBMIT_CONSOLE = 1
    RR_SUBMIT_API = 2

    def __init__(self, rr_path=None):
        self.log = Logger.get_logger("RoyalRender")
        self._rr_path = rr_path
        os.environ["RR_ROOT"] = rr_path

    @staticmethod
    def get_rr_bin_path(rr_root, tool_name=None):
        # type: (str, str) -> str
        """Get path to RR bin folder.

        Args:
            tool_name (str): Name of RR executable you want.
            rr_root (str): Custom RR root if needed.

        Returns:
            str: Path to the tool based on current platform.

        """
        is_64bit_python = sys.maxsize > 2 ** 32

        rr_bin_parts = [rr_root, "bin"]
        if sys.platform.lower() == "win32":
            rr_bin_parts.append("win")

        if sys.platform.lower() == "darwin":
            rr_bin_parts.append("mac")

        if sys.platform.lower().startswith("linux"):
            rr_bin_parts.append("lx")

        rr_bin_path = os.sep.join(rr_bin_parts)

        paths_to_check = []
        # if we use 64bit python, append 64bit specific path first
        if is_64bit_python:
            if not tool_name:
                return rr_bin_path + "64"
            paths_to_check.append(rr_bin_path + "64")

        # otherwise use 32bit
        if not tool_name:
            return rr_bin_path
        paths_to_check.append(rr_bin_path)

        return find_tool_in_custom_paths(paths_to_check, tool_name)

    def _initialize_module_path(self):
        # type: () -> None
        """Set RR modules for Python."""
        # default for linux
        rr_bin = self.get_rr_bin_path(self._rr_path)
        rr_module_path = os.path.join(rr_bin, "lx64/lib")

        if sys.platform.lower() == "win32":
            rr_module_path = rr_bin
            rr_module_path = rr_module_path.replace(
                "/", os.path.sep
            )

        if sys.platform.lower() == "darwin":
            rr_module_path = os.path.join(rr_bin, "lib/python/27")

        sys.path.append(os.path.join(self._rr_path, rr_module_path))

    @staticmethod
    def create_submission(jobs, submitter_attributes):
        # type: (list[RRJob], list[SubmitterParameter]) -> SubmitFile
        """Create jobs submission file.

        Args:
            jobs (list): List of :class:`RRJob`
            submitter_attributes (list): List of submitter attributes
                :class:`SubmitterParameter` for whole submission batch.

        Returns:
            str: XML data of job submission files.

        """
        return SubmitFile(SubmitterParameters=submitter_attributes, Jobs=jobs)

    def submit_file(self, file, mode=RR_SUBMIT_CONSOLE):
        # type: (SubmitFile, int) -> None
        if mode == self.RR_SUBMIT_CONSOLE:
            self._submit_using_console(file)
            return

        # RR v7 supports only Python 2.7, so we bail out in fear
        # until there is support for Python 3 😰
        raise NotImplementedError(
            "Submission via RoyalRender API is not supported yet")
        # self._submit_using_api(file)

    def _submit_using_console(self, job_file):
        # type: (SubmitFile) -> None
        rr_start_local = self.get_rr_bin_path(
            self._rr_path, "rrStartLocal")

        self.log.info("rr_console: {}".format(rr_start_local))

        args = [rr_start_local, "rrSubmitterconsole", job_file]
        self.log.info("Executing: {}".format(" ".join(args)))
        env = os.environ
        env["RR_ROOT"] = self._rr_path
        run_subprocess(args, logger=self.log, env=env)

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
            self.log.info("Got RR IP address {}".format(rr_server))

        # TODO: Port is hardcoded in RR? If not, move it to Settings
        if not tcp.setServer(rr_server, 7773):
            self.log.error(
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
