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
    def initialize(self, module_settings):
        """Initialization of module attributes.

        It is not recommended to override __init__ that's why specific method
        was implemented.
        """
        pass

    @abstractmethod
    def connect_with_modules(self, enabled_modules):
        """Connect with other enabled modules."""
        pass

    def get_global_environments(self):
        """Get global environments values of module.

        Environment variables that can be get only from system settings.
        """
        return {}


@six.add_metaclass(ABCMeta)
class ITrayModule:
    """Module has special procedures when used in Pype Tray.

    IMPORTANT:
    The module still must be usable if is not used in tray even if
    would do nothing.
    """
    tray_initialized = False

    def do_tray_init(self, *args, **kwargs):
        """Method called by Tray manager.

        Point is to set `tray_initialized` to True after process.

        TODO try to handle this with decorator on `tray_init`.
        """
        self.tray_init(*args, **kwargs)
        self.tray_initialized = True

    @abstractmethod
    def tray_init(self, tray_widget, main_window):
        """Initialization part of tray implementation.

        Triggered between `initialization` and `connect_with_modules`.

        This is where GUIs should be loaded or tray specific parts should be
        prepared.
        """
        pass

    @abstractmethod
    def tray_menu(self, tray_menu):
        """Add module's action to tray menu."""
        pass

    @abstractmethod
    def tray_start(self):
        """Start procedure in Pype tray."""
        pass

    @abstractmethod
    def tray_exit(self):
        """Cleanup method which is executed on tray shutdown.

        This is place where all threads should be shut.
        """
        pass
