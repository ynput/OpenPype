#! python3

"""
Fusion tools for setting environment
"""

import os
import shutil

from openpype.api import Logger
import openpype.hosts.fusion

log = Logger().get_logger(__name__)


def setup(env=None):
    """ Wrapper installer started from pype.hooks.fusion.FusionPrelaunch()
    """
    if not env:
        env = os.environ

    # todo(roy): This currently does nothing. Remove?

    log.info("Fusion Pype wrapper has been installed")
