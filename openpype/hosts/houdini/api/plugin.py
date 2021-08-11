# -*- coding: utf-8 -*-
"""Houdini specific Avalon/Pyblish plugin definitions."""

import sys

from avalon import houdini
import hou
import six
from openpype.api import PypeCreatorMixin


class Creator(PypeCreatorMixin, houdini.Creator):
    def process(self):
        # reraise as standard Python exception so
        # Avalon can catch it
        try:
            self._process()
        except hou.Error as er:
            six.reraise(Exception, er, sys.exc_info()[2])
