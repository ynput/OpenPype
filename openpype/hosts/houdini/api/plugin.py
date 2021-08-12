# -*- coding: utf-8 -*-
"""Houdini specific Avalon/Pyblish plugin definitions."""
from avalon import houdini
import hou
from openpype.api import PypeCreatorMixin


class Creator(PypeCreatorMixin, houdini.Creator):
    def process(self):
        # reraise as standard Python exception so
        # Avalon can catch it
        try:
            self._process()
        except hou.Error as er:
            # cannot do re-raise with six as it will cause
            # infinite recursion.
            raise Exception(er)
