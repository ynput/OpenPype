# -*- coding: utf-8 -*-
"""Base class for Pype Modules."""
from uuid import uuid4
from abc import ABCMeta, abstractmethod
import six

from pype.lib import PypeLogger
from pype import resources


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


class ITrayService(ITrayModule):
    menu_action = None
    # Class properties
    _services_submenu = None
    _icon_failed = None
    _icon_running = None
    _icon_idle = None

    @property
    @abstractmethod
    def label(self):
        """Service label."""
        pass

    # TODO be able to get any sort of information to show/print
    # @abstractmethod
    # def get_service_info(self):
    #     pass

    @classmethod
    def services_submenu(cls):
        return cls._services_submenu

    @classmethod
    def _load_service_icons(cls):
        from Qt import QtGui
        cls._failed_icon = QtGui.QIcon(
            resources.get_resource("icons", "circle_red.png")
        )
        cls._icon_running = QtGui.QIcon(
            resources.get_resource("icons", "circle_green.png")
        )
        cls._icon_idle = QtGui.QIcon(
            resources.get_resource("icons", "circle_orange.png")
        )

    @classmethod
    def get_icon_running(cls):
        if cls._icon_running is None:
            cls._load_service_icons()
        return cls._icon_running

    @classmethod
    def get_icon_idle(cls):
        if cls._icon_idle is None:
            cls._load_service_icons()
        return cls._icon_idle

    @classmethod
    def get_icon_failed(cls):
        if cls._failed_icon is None:
            cls._load_service_icons()
        return cls._failed_icon

    def tray_menu(self, tray_menu):
        from Qt import QtWidgets
        services_submenu = self.services_submenu()
        if services_submenu is None:
            services_submenu = QtWidgets.QMenu("Services", tray_menu)
            self.__class__._services_submenu = services_submenu

        action = QtWidgets.QAction(self.label, services_submenu)
        services_submenu.addAction(action)

        self.menu_action = action

        self.set_service_running()

    def set_service_running(self):
        if self.menu_action:
            self.menu_action.setIcon(self.get_icon_running())

    def set_service_failed(self):
        if self.menu_action:
            self.menu_action.setIcon(self.get_icon_failed())

    def set_service_idle(self):
        if self.menu_action:
            self.menu_action.setIcon(self.get_icon_idle())
