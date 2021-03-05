# -*- coding: utf-8 -*-
"""Base class for Pype Modules."""
import time
import inspect
import logging
import collections
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


@six.add_metaclass(ABCMeta)
class ILaunchHookPaths:
    """Module has launch hook paths to return.

    Expected result is list of paths.
    ["path/to/launch_hooks_dir"]
    """

    @abstractmethod
    def get_launch_hook_paths(self):
        pass


@six.add_metaclass(ABCMeta)
class ITrayModule:
    """Module has special procedures when used in Pype Tray.

    IMPORTANT:
    The module still must be usable if is not used in tray even if
    would do nothing.
    """
    tray_initialized = False

    @abstractmethod
    def tray_init(self):
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


class ITrayAction(ITrayModule):
    """Implementation of Tray action.

    Add action to tray menu which will trigger `on_action_trigger`.
    It is expected to be used for showing tools.

    Methods `tray_start`, `tray_exit` and `connect_with_modules` are overriden
    as it's not expected that action will use them. But it is possible if
    necessary.
    """

    @property
    @abstractmethod
    def label(self):
        """Service label showed in menu."""
        pass

    @abstractmethod
    def on_action_trigger(self):
        """What happens on actions click."""
        pass

    def tray_menu(self, tray_menu):
        from Qt import QtWidgets
        action = QtWidgets.QAction(self.label, tray_menu)
        action.triggered.connect(self.on_action_trigger)
        tray_menu.addAction(action)

    def tray_start(self):
        return

    def tray_exit(self):
        return


class ITrayService(ITrayModule):
    # Module's property
    menu_action = None

    # Class properties
    _services_submenu = None
    _icon_failed = None
    _icon_running = None
    _icon_idle = None

    @property
    @abstractmethod
    def label(self):
        """Service label showed in menu."""
        pass

    # TODO be able to get any sort of information to show/print
    # @abstractmethod
    # def get_service_info(self):
    #     pass

    @staticmethod
    def services_submenu(tray_menu):
        if ITrayService._services_submenu is None:
            from Qt import QtWidgets
            services_submenu = QtWidgets.QMenu("Services", tray_menu)
            services_submenu.menuAction().setVisible(False)
            ITrayService._services_submenu = services_submenu
        return ITrayService._services_submenu

    @staticmethod
    def add_service_action(action):
        ITrayService._services_submenu.addAction(action)
        if not ITrayService._services_submenu.menuAction().isVisible():
            ITrayService._services_submenu.menuAction().setVisible(True)

    @staticmethod
    def _load_service_icons():
        from Qt import QtGui
        ITrayService._failed_icon = QtGui.QIcon(
            resources.get_resource("icons", "circle_red.png")
        )
        ITrayService._icon_running = QtGui.QIcon(
            resources.get_resource("icons", "circle_green.png")
        )
        ITrayService._icon_idle = QtGui.QIcon(
            resources.get_resource("icons", "circle_orange.png")
        )

    @staticmethod
    def get_icon_running():
        if ITrayService._icon_running is None:
            ITrayService._load_service_icons()
        return ITrayService._icon_running

    @staticmethod
    def get_icon_idle():
        if ITrayService._icon_idle is None:
            ITrayService._load_service_icons()
        return ITrayService._icon_idle

    @staticmethod
    def get_icon_failed():
        if ITrayService._failed_icon is None:
            ITrayService._load_service_icons()
        return ITrayService._failed_icon

    def tray_menu(self, tray_menu):
        from Qt import QtWidgets
        action = QtWidgets.QAction(
            self.label,
            self.services_submenu(tray_menu)
        )
        self.menu_action = action

        self.add_service_action(action)

        self.set_service_running_icon()

    def set_service_running_icon(self):
        """Change icon of an QAction to green circle."""
        if self.menu_action:
            self.menu_action.setIcon(self.get_icon_running())

    def set_service_failed_icon(self):
        """Change icon of an QAction to red circle."""
        if self.menu_action:
            self.menu_action.setIcon(self.get_icon_failed())

    def set_service_idle_icon(self):
        """Change icon of an QAction to orange circle."""
        if self.menu_action:
            self.menu_action.setIcon(self.get_icon_idle())


class ModulesManager:
    # Helper attributes for report
    _report_total_key = "Total"

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

        self.modules = []
        self.modules_by_id = {}
        self.modules_by_name = {}
        # For report of time consumption
        self._report = {}

        self.initialize_modules()
        self.connect_modules()

    def initialize_modules(self):
        """Import and initialize modules."""
        self.log.debug("*** Pype modules initialization.")
        # Prepare settings for modules
        modules_settings = get_system_settings()["modules"]

        report = {}
        time_start = time.time()
        prev_start_time = time_start

        # Go through globals in `pype.modules`
        for name in dir(pype.modules):
            modules_item = getattr(pype.modules, name, None)
            # Filter globals that are not classes which inherit from PypeModule
            if (
                not inspect.isclass(modules_item)
                or modules_item is pype.modules.PypeModule
                or not issubclass(modules_item, pype.modules.PypeModule)
            ):
                continue

            # Check if class is abstract (Developing purpose)
            if inspect.isabstract(modules_item):
                # Find missing implementations by convetion on `abc` module
                not_implemented = []
                for attr_name in dir(modules_item):
                    attr = getattr(modules_item, attr_name, None)
                    if attr and getattr(attr, "__isabstractmethod__", None):
                        not_implemented.append(attr_name)

                # Log missing implementations
                self.log.warning((
                    "Skipping abstract Class: {}. Missing implementations: {}"
                ).format(name, ", ".join(not_implemented)))
                continue

            try:
                # Try initialize module
                module = modules_item(self, modules_settings)
                # Store initialized object
                self.modules.append(module)
                self.modules_by_id[module.id] = module
                self.modules_by_name[module.name] = module
                enabled_str = "X"
                if not module.enabled:
                    enabled_str = " "
                self.log.debug("[{}] {}".format(enabled_str, name))

                now = time.time()
                report[module.__class__.__name__] = now - prev_start_time
                prev_start_time = now

            except Exception:
                self.log.warning(
                    "Initialization of module {} failed.".format(name),
                    exc_info=True
                )

        if self._report is not None:
            report[self._report_total_key] = time.time() - time_start
            self._report["Initialization"] = report

    def connect_modules(self):
        """Trigger connection with other enabled modules.

        Modules should handle their interfaces in `connect_with_modules`.
        """
        report = {}
        time_start = time.time()
        prev_start_time = time_start
        enabled_modules = self.get_enabled_modules()
        self.log.debug("Has {} enabled modules.".format(len(enabled_modules)))
        for module in enabled_modules:
            try:
                module.connect_with_modules(enabled_modules)
            except Exception:
                self.log.error(
                    "BUG: Module failed on connection with other modules.",
                    exc_info=True
                )

            now = time.time()
            report[module.__class__.__name__] = now - prev_start_time
            prev_start_time = now

        if self._report is not None:
            report[self._report_total_key] = time.time() - time_start
            self._report["Connect modules"] = report

    def get_enabled_modules(self):
        """Enabled modules initialized by the manager.

        Returns:
            list: Initialized and enabled modules.
        """
        return [
            module
            for module in self.modules
            if module.enabled
        ]

    def collect_global_environments(self):
        """Helper to collect global enviornment variabled from modules.

        Returns:
            dict: Global environment variables from enabled modules.

        Raises:
            AssertionError: Gobal environment variables must be unique for
                all modules.
        """
        module_envs = {}
        for module in self.get_enabled_modules():
            # Collect global module's global environments
            _envs = module.get_global_environments()
            for key, value in _envs.items():
                if key in module_envs:
                    # TODO better error message
                    raise AssertionError(
                        "Duplicated environment key {}".format(key)
                    )
                module_envs[key] = value
        return module_envs

    def collect_plugin_paths(self):
        """Helper to collect all plugins from modules inherited IPluginPaths.

        Unknown keys are logged out.

        Returns:
            dict: Output is dictionary with keys "publish", "create", "load"
                and "actions" each containing list of paths.
        """
        # Output structure
        output = {
            "publish": [],
            "create": [],
            "load": [],
            "actions": []
        }
        unknown_keys_by_module = {}
        for module in self.get_enabled_modules():
            # Skip module that do not inherit from `IPluginPaths`
            if not isinstance(module, IPluginPaths):
                continue
            plugin_paths = module.get_plugin_paths()
            for key, value in plugin_paths.items():
                # Filter unknown keys
                if key not in output:
                    if module.name not in unknown_keys_by_module:
                        unknown_keys_by_module[module.name] = []
                    unknown_keys_by_module[module.name].append(key)
                    continue

                # Skip if value is empty
                if not value:
                    continue

                # Convert to list if value is not list
                if not isinstance(value, (list, tuple, set)):
                    value = [value]
                output[key].extend(value)

        # Report unknown keys (Developing purposes)
        if unknown_keys_by_module:
            expected_keys = ", ".join([
                "\"{}\"".format(key) for key in output.keys()
            ])
            msg_template = "Module: \"{}\" - got key {}"
            msg_items = []
            for module_name, keys in unknown_keys_by_module.items():
                joined_keys = ", ".join([
                    "\"{}\"".format(key) for key in keys
                ])
                msg_items.append(msg_template.format(module_name, joined_keys))
            self.log.warning((
                "Expected keys from `get_plugin_paths` are {}. {}"
            ).format(expected_keys, " | ".join(msg_items)))
        return output

    def collect_launch_hook_paths(self):
        """Helper to collect hooks from modules inherited ILaunchHookPaths.

        Returns:
            list: Paths to launch hook directories.
        """
        str_type = type("")
        expected_types = (list, tuple, set)

        output = []
        for module in self.get_enabled_modules():
            # Skip module that do not inherit from `ILaunchHookPaths`
            if not isinstance(module, ILaunchHookPaths):
                continue

            hook_paths = module.get_launch_hook_paths()
            if not hook_paths:
                continue

            # Convert string to list
            if isinstance(hook_paths, str_type):
                hook_paths = [hook_paths]

            # Skip invalid types
            if not isinstance(hook_paths, expected_types):
                self.log.warning((
                    "Result of `get_launch_hook_paths`"
                    " has invalid type {}. Expected {}"
                ).format(type(hook_paths), expected_types))
                continue

            output.extend(hook_paths)
        return output

    def print_report(self):
        """Print out report of time spent on modules initialization parts.

        Reporting is not automated must be implemented for each initialization
        part separatelly. Reports must be stored to `_report` attribute.
        Print is skipped if `_report` is empty.

        Attribute `_report` is dictionary where key is "label" describing
        the processed part and value is dictionary where key is module's
        class name and value is time delta of it's processing.

        It is good idea to add total time delta on processed part under key
        which is defined in attribute `_report_total_key`. By default has value
        `"Total"` but use the attribute please.

        ```javascript
        {
            "Initialization": {
                "FtrackModule": 0.003,
                ...
                "Total": 1.003,
            },
            ...
        }
        ```
        """
        if not self._report:
            return

        available_col_names = set()
        for module_names in self._report.values():
            available_col_names |= set(module_names.keys())

        # Prepare ordered dictionary for columns
        cols = collections.OrderedDict()
        # Add module names to first columnt
        cols["Module name"] = list(sorted(
            module.__class__.__name__
            for module in self.modules
            if module.__class__.__name__ in available_col_names
        ))
        # Add total key (as last module)
        cols["Module name"].append(self._report_total_key)

        # Add columns from report
        for label in self._report.keys():
            cols[label] = []

        total_module_times = {}
        for module_name in cols["Module name"]:
            total_module_times[module_name] = 0

        for label, reported in self._report.items():
            for module_name in cols["Module name"]:
                col_time = reported.get(module_name)
                if col_time is None:
                    cols[label].append("N/A")
                    continue
                cols[label].append("{:.3f}".format(col_time))
                total_module_times[module_name] += col_time

        # Add to also total column that should sum the row
        cols[self._report_total_key] = []
        for module_name in cols["Module name"]:
            cols[self._report_total_key].append(
                "{:.3f}".format(total_module_times[module_name])
            )

        # Prepare column widths and total row count
        # - column width is by
        col_widths = {}
        total_rows = None
        for key, values in cols.items():
            if total_rows is None:
                total_rows = 1 + len(values)
            max_width = len(key)
            for value in values:
                value_length = len(value)
                if value_length > max_width:
                    max_width = value_length
            col_widths[key] = max_width

        rows = []
        for _idx in range(total_rows):
            rows.append([])

        for key, values in cols.items():
            width = col_widths[key]
            idx = 0
            rows[idx].append(key.ljust(width))
            for value in values:
                idx += 1
                rows[idx].append(value.ljust(width))

        filler_parts = []
        for width in col_widths.values():
            filler_parts.append(width * "-")
        filler = "+".join(filler_parts)

        formatted_rows = [filler]
        last_row_idx = len(rows) - 1
        for idx, row in enumerate(rows):
            # Add filler before last row
            if idx == last_row_idx:
                formatted_rows.append(filler)

            formatted_rows.append("|".join(row))

            # Add filler after first row
            if idx == 0:
                formatted_rows.append(filler)

        # Join rows with newline char and add new line at the end
        output = "\n".join(formatted_rows) + "\n"
        print(output)


class TrayModulesManager(ModulesManager):
    # Define order of modules in menu
    modules_menu_order = (
        "user",
        "ftrack",
        "muster",
        "launcher_tool",
        "avalon",
        "clockify",
        "standalonepublish_tool",
        "log_viewer",
        "local_settings",
        "settings"
    )

    def __init__(self):
        self.log = PypeLogger().get_logger(self.__class__.__name__)

        self.modules = []
        self.modules_by_id = {}
        self.modules_by_name = {}
        self._report = {}
        self.tray_manager = None

    def initialize(self, tray_manager, tray_menu):
        self.tray_manager = tray_manager
        self.initialize_modules()
        self.tray_init()
        self.connect_modules()
        self.tray_menu(tray_menu)

    def get_enabled_tray_modules(self):
        output = []
        for module in self.modules:
            if module.enabled and isinstance(module, ITrayModule):
                output.append(module)
        return output

    def tray_init(self):
        report = {}
        time_start = time.time()
        prev_start_time = time_start
        for module in self.get_enabled_tray_modules():
            try:
                module.tray_init()
                module.tray_initialized = True
            except Exception:
                self.log.warning(
                    "Module \"{}\" crashed on `tray_init`.".format(
                        module.name
                    ),
                    exc_info=True
                )

            now = time.time()
            report[module.__class__.__name__] = now - prev_start_time
            prev_start_time = now

        if self._report is not None:
            report[self._report_total_key] = time.time() - time_start
            self._report["Tray init"] = report

    def tray_menu(self, tray_menu):
        ordered_modules = []
        enabled_by_name = {
            module.name: module
            for module in self.get_enabled_tray_modules()
        }

        for name in self.modules_menu_order:
            module_by_name = enabled_by_name.pop(name, None)
            if module_by_name:
                ordered_modules.append(module_by_name)
        ordered_modules.extend(enabled_by_name.values())

        report = {}
        time_start = time.time()
        prev_start_time = time_start
        for module in ordered_modules:
            if not module.tray_initialized:
                continue

            try:
                module.tray_menu(tray_menu)
            except Exception:
                # Unset initialized mark
                module.tray_initialized = False
                self.log.warning(
                    "Module \"{}\" crashed on `tray_menu`.".format(
                        module.name
                    ),
                    exc_info=True
                )
            now = time.time()
            report[module.__class__.__name__] = now - prev_start_time
            prev_start_time = now

        if self._report is not None:
            report[self._report_total_key] = time.time() - time_start
            self._report["Tray menu"] = report

    def start_modules(self):
        report = {}
        time_start = time.time()
        prev_start_time = time_start
        for module in self.get_enabled_tray_modules():
            if not module.tray_initialized:
                if isinstance(module, ITrayService):
                    module.set_service_failed_icon()
                continue

            try:
                module.tray_start()
            except Exception:
                self.log.warning(
                    "Module \"{}\" crashed on `tray_start`.".format(
                        module.name
                    ),
                    exc_info=True
                )
            now = time.time()
            report[module.__class__.__name__] = now - prev_start_time
            prev_start_time = now

        if self._report is not None:
            report[self._report_total_key] = time.time() - time_start
            self._report["Modules start"] = report

    def on_exit(self):
        for module in self.get_enabled_tray_modules():
            if module.tray_initialized:
                try:
                    module.tray_exit()
                except Exception:
                    self.log.warning(
                        "Module \"{}\" crashed on `tray_exit`.".format(
                            module.name
                        ),
                        exc_info=True
                    )
