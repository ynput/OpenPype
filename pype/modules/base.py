# -*- coding: utf-8 -*-
"""Base class for Pype Modules."""
from uuid import uuid4
from abc import ABCMeta, abstractmethod
import six

from pype.lib import PypeLogger


@six.add_metaclass(ABCMeta)
class PypeModule:
    """Base class of pype module.

    Attributes:
        id (UUID): Module id.
        enabled (bool): Is module enabled.
        name (str): Module name.
    """

    enabled = False
    _id = None
    @property
    @abstractmethod
    def name(self):
        """Module's name."""
        pass

    def __init__(self, manager, settings):
        self.manager = manager

        self.log = PypeLogger().get_logger(self.name)

        self.initialize(settings)

    @property
    def id(self):
        if self._id is None:
            self._id = uuid4()
        return self._id

    @abstractmethod
    def startup_environments(self):
        """Get startup environments for module."""
        return {}
