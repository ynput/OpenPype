# -*- coding: utf-8 -*-
"""Prelaunch hook for Maya.

This hook automatically open latest workfile upon startup.
"""

import logging
import os
from pype.lib import PypeHook
from pype.api import (
    Logger,
    get_last_version_from_path
)

log = logging.getLogger(__name__)


class MayaPrelaunchHook(PypeHook):
    """Prelaunch hook."""

    workfile_ext = "scn"

    def __init__(self, logger=None):
        """Constructor."""
        if not logger:
            self.log = Logger().get_logger(self.__class__.__name__)
        else:
            self.log = logger

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self, *args, env: dict = None) -> bool:
        """Execute method.

        Args:
            env (dict): environment of application to be launched.

        Returns:
            True on success.

        """
        if not env:
            env = os.environ

        ma = get_last_version_from_path(env.get("AVALON_WORKDIR"), [".ma"])
        mb = get_last_version_from_path(env.get("AVALON_WORKDIR"), [".mb"])

        if not ma or not mb:
            return True

        last = sorted([ma, mb])[-1]

        env["PYPE_OPEN_WORKFILE"] = os.path.join(
            env.get("AVALON_WORKDIR"), last)

        self.log.info("--- using latest workfile at [ {} ]".format(
            env["PYPE_OPEN_WORKFILE"]))
        return True
