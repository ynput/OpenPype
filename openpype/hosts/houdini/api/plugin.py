# -*- coding: utf-8 -*-
"""Houdini specific Avalon/Pyblish plugin definitions."""
import sys
from avalon.api import CreatorError
from avalon import houdini
import six

import hou
from openpype.api import PypeCreatorMixin


class OpenPypeCreatorError(CreatorError):
    pass


class Creator(PypeCreatorMixin, houdini.Creator):
    def process(self):
        try:
            # re-raise as standard Python exception so
            # Avalon can catch it
            instance = super(Creator, self).process()
            self._process(instance)
        except hou.Error as er:
            six.reraise(
                OpenPypeCreatorError,
                OpenPypeCreatorError("Creator error: {}".format(er)),
                sys.exc_info()[2])
