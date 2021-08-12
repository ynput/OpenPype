# -*- coding: utf-8 -*-
"""Houdini specific Avalon/Pyblish plugin definitions."""
import sys
from avalon import houdini
import six

import hou
from openpype.api import PypeCreatorMixin


class OpenPypeCreatorError(Exception):
    pass


class Creator(PypeCreatorMixin, houdini.Creator):
    def process(self):
        instance = super(houdini.Creator, self).process()
        # re-raise as standard Python exception so
        # Avalon can catch it
        try:
            self._process(instance)
        except hou.Error as er:
            six.reraise(OpenPypeCreatorError, OpenPypeCreatorError("Creator error"), sys.exc_info()[2])
