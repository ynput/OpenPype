# -*- coding: utf-8 -*-
"""Base class for Pype Modules."""
import inspect
import logging
from uuid import uuid4
from abc import ABCMeta, abstractmethod
import six

import pype
from pype.settings import get_system_settings
from pype.lib import PypeLogger
from pype import resources


@six.add_metaclass(ABCMeta)
class PypeModule:
    """Base class of pype module.

    Attributes:
        id (UUID): Module's id.
        enabled (bool): Is module enabled.
        name (str): Module name.
        manager (ModulesManager): Manager that created the module.
    """

    # Disable by default
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


@six.add_metaclass(ABCMeta)
class IPluginPaths:
    """Module has plugin paths to return.

    Expected result is dictionary with keys "publish", "create", "load" or
    "actions" and values as list or string.
    {
        "publish": ["path/to/publish_plugins"]
    }
    """
    # TODO validation of an output
    @abstractmethod
    def get_plugin_paths(self):
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


class ModulesManager:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

        self.modules = {}

        self.initialize_modules()
        self.connect_modules()

    def initialize_modules(self):
        self.log.debug("*** Pype modules initialization.")
        modules_settings = get_system_settings()["modules"]
        for name in dir(pype.modules):
            modules_item = getattr(pype.modules, name, None)
            if (
                not inspect.isclass(modules_item)
                or modules_item is pype.modules.PypeModule
                or not issubclass(modules_item, pype.modules.PypeModule)
            ):
                continue

            if inspect.isabstract(modules_item):
                not_implemented = []
                for attr_name in dir(modules_item):
                    attr = getattr(modules_item, attr_name, None)
                    if attr and getattr(attr, "__isabstractmethod__", None):
                        not_implemented.append(attr_name)

                self.log.warning((
                    "Skipping abstract Class: {}. Missing implementations: {}"
                ).format(name, ", ".join(not_implemented)))
                continue

            try:
                module = modules_item(self, modules_settings)
                self.modules[module.id] = module
                enabled_str = "X"
                if not module.enabled:
                    enabled_str = " "
                self.log.debug("[{}] {}".format(enabled_str, name))

            except Exception:
                self.log.warning(
                    "Initialization of module {} failed.".format(name),
                    exc_info=True
                )

    def connect_modules(self):
        enabled_modules = self.get_enabled_modules()
        self.log.debug("Has {} enabled modules.".format(len(enabled_modules)))
        for module in enabled_modules:
            module.connect_with_modules(enabled_modules)

    def get_enabled_modules(self):
        return [
            module
            for module in self.modules.values()
            if module.enabled
        ]


class TrayModulesManager(ModulesManager):
    def __init__(self):
        self.log = PypeLogger().get_logger(self.__class__.__name__)

        self.modules = {}

    def initialize(self, tray_widget, main_window):
        self.tray_widget = tray_widget
        self.main_window = main_window

        self.initialize_modules()
        self.tray_init(tray_widget, main_window)
        self.connect_modules()

    def get_enabled_tray_modules(self):
        output = []
        for module in self.modules.values():
            if module.enabled and isinstance(module, ITrayModule):
                output.append(module)
        return output

    def tray_init(self, *args, **kwargs):
        for module in self.get_enabled_tray_modules():
            module.do_tray_init(*args, **kwargs)

    def tray_menu(self, tray_menu):
        for module in self.get_enabled_tray_modules():
            module.tray_menu(tray_menu)

    def start_modules(self):
        for module in self.get_enabled_tray_modules():
            module.tray_start()

    def on_exit(self):
        for module in self.get_enabled_tray_modules():
            module.tray_exit()
