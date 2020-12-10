# -*- coding: utf-8 -*-
"""Base class for Pype Modules."""
from uuid import uuid4
from pype.api import Logger
from abc import ABCMeta, abstractmethod
import six



@six.add_metaclass(ABCMeta)
class PypeModule:
    """Base class of pype module.

    Attributes:
        id (UUID): Module id.
        enabled (bool): Is module enabled.
        name (str): Module name.
    """

    enabled = False
    name = None
    _id = None

    def __init__(self, settings):
        if self.name is None:
            self.name = self.__class__.__name__

        self.log = Logger().get_logger(self.name)

        self.settings = settings.get(self.name)
        self.enabled = settings.get("enabled", False)
        self._id = uuid4()

    @property
    def id(self):
        return self._id

    @abstractmethod
    def startup_environments(self):
        """Get startup environments for module."""
        return {}
