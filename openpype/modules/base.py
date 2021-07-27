# -*- coding: utf-8 -*-
"""Base class for Pype Modules."""
import os
import sys
import types
import time
import inspect
import logging
import collections
from uuid import uuid4
from abc import ABCMeta, abstractmethod
import six

import openpype
from openpype.settings import get_system_settings
from openpype.lib import PypeLogger


class __ModuleClass:
    def __init__(self):
        self.object_setattr("__attributes__", {})
        self.object_setattr("__defaults__", set())

    def __getattr__(self, attr_name):
        return self.__attributes__.get(
            attr_name,
            type("Missing.{}".format(attr_name), (), {})
        )

    def __iter__(self):
        for module in self.values():
            yield module

    def object_setattr(self, attr_name, value):
        object.__setattr__(self, attr_name, value)

    def __setattr__(self, attr_name, value):
        self.__attributes__[attr_name] = value

    def keys(self):
        return self.__attributes__.keys()

    def values(self):
        return self.__attributes__.values()

    def items(self):
        return self.__attributes__.items()


def load_interfaces(force=False):
    if not force and "openpype_interfaces" in sys.modules:
        return

    sys.modules["openpype_interfaces"] = openpype_interfaces = __ModuleClass()

    log = PypeLogger.get_logger("InterfacesLoader")

    current_dir = os.path.abspath(os.path.dirname(__file__))

    interface_paths = [
        os.path.join(current_dir, "interfaces.py")
    ]

    for filename in os.listdir(current_dir):
        full_path = os.path.join(current_dir, filename)
        if os.path.isdir(full_path):
            interface_paths.append(
                os.path.join(full_path, "interfaces.py")
            )

    # print(interface_paths)
    for full_path in interface_paths:
        if not os.path.exists(full_path):
            continue

        filename = os.path.splitext(os.path.basename(full_path))[0]

        try:
            # Prepare module object where content of file will be parsed
            module = types.ModuleType(filename)

            if six.PY3:
                import importlib

                # Use loader so module has full specs
                module_loader = importlib.machinery.SourceFileLoader(
                    filename, full_path
                )
                module_loader.exec_module(module)
            else:
                # Execute module code and store content to module
                with open(full_path) as _stream:
                    # Execute content and store it to module object
                    exec(_stream.read(), module.__dict__)

                module.__file__ = full_path

        except Exception:
            log.warning(
                "Failed to load path: \"{0}\"".format(full_path),
                exc_info=True
            )
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                not inspect.isclass(attr)
                or attr is OpenPypeInterface
                or not issubclass(attr, OpenPypeInterface)
            ):
                continue
            setattr(openpype_interfaces, attr_name, attr)


def load_modules(force=False):
    if not force and "openpype_modules" in sys.modules:
        return

    from openpype.lib import modules_from_path

    sys.modules["openpype_modules"] = openpype_modules = __ModuleClass()

    log = PypeLogger.get_logger("ModulesLoader")

    from . import (
        avalon_apps,
        clockify,
        deadline,
        ftrack,
        idle_manager,
        log_viewer,
        muster,
        settings_module,
        slack,
        sync_server,
        timers_manager,
        webserver,
        standalonepublish_action,
        project_manager_action
    )
    setattr(openpype_modules, "avalon_apps", avalon_apps)
    setattr(openpype_modules, "clockify", clockify)
    setattr(openpype_modules, "deadline", deadline)
    setattr(openpype_modules, "ftrack", ftrack)
    setattr(openpype_modules, "idle_manager", idle_manager)
    setattr(openpype_modules, "log_viewer", log_viewer)
    setattr(openpype_modules, "muster", muster)
    setattr(openpype_modules, "settings_module", settings_module)
    setattr(openpype_modules, "sync_server", sync_server)
    setattr(openpype_modules, "slack", slack)
    setattr(openpype_modules, "timers_manager", timers_manager)
    setattr(openpype_modules, "webserver", webserver)
    setattr(
        openpype_modules, "standalonepublish_action", standalonepublish_action
    )
    setattr(openpype_modules, "project_manager_action", project_manager_action)


@six.add_metaclass(ABCMeta)
class OpenPypeInterface:
    """Base class of Interface that can be used as Mixin with abstract parts.

    This is way how OpenPype module or addon can tell that has implementation
    for specific part or for other module/addon.
    """
    pass


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


class OpenPypeAddOn(PypeModule):
    pass


class ModulesManager:
    """Manager of Pype modules helps to load and prepare them to work.

    Args:
        modules_settings(dict): To be able create module manager with specified
            data. For settings changes callbacks and testing purposes.
    """
    # Helper attributes for report
    _report_total_key = "Total"

    def __init__(self, _system_settings=None):
        self.log = logging.getLogger(self.__class__.__name__)

        self._system_settings = _system_settings

        self.modules = []
        self.modules_by_id = {}
        self.modules_by_name = {}
        # For report of time consumption
        self._report = {}

        self.initialize_modules()
        self.connect_modules()

    def collect_modules(self):
        load_interfaces()
        load_modules()

    def initialize_modules(self):
        """Import and initialize modules."""
        self.collect_modules()

        import openpype_modules

        self.log.debug("*** Pype modules initialization.")
        # Prepare settings for modules
        system_settings = getattr(self, "_system_settings", None)
        if system_settings is None:
            system_settings = get_system_settings()
        modules_settings = system_settings["modules"]

        report = {}
        time_start = time.time()
        prev_start_time = time_start

        module_classes = []
        for module in openpype_modules:
            # Go through globals in `pype.modules`
            for name in dir(module):
                modules_item = getattr(module, name, None)
                # Filter globals that are not classes which inherit from
                #   PypeModule
                if (
                    not inspect.isclass(modules_item)
                    or modules_item is PypeModule
                    or not issubclass(modules_item, PypeModule)
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
                module_classes.append(modules_item)

        for modules_item in module_classes:
            try:
                name = modules_item.__name__
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
        from openpype_interfaces import IPluginPaths

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
        from openpype_interfaces import ILaunchHookPaths

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
        self.log = PypeLogger.get_logger(self.__class__.__name__)

        self.modules = []
        self.modules_by_id = {}
        self.modules_by_name = {}
        self._report = {}

        self.tray_manager = None

        self.doubleclick_callbacks = {}
        self.doubleclick_callback = None

    def add_doubleclick_callback(self, module, callback):
        """Register doubleclick callbacks on tray icon.

        Currently there is no way how to determine which is launched. Name of
        callback can be defined with `doubleclick_callback` attribute.

        Missing feature how to define default callback.
        """
        callback_name = "_".join([module.name, callback.__name__])
        if callback_name not in self.doubleclick_callbacks:
            self.doubleclick_callbacks[callback_name] = callback
            if self.doubleclick_callback is None:
                self.doubleclick_callback = callback_name
            return

        self.log.warning((
            "Callback with name \"{}\" is already registered."
        ).format(callback_name))

    def initialize(self, tray_manager, tray_menu):
        self.tray_manager = tray_manager
        self.initialize_modules()
        self.tray_init()
        self.connect_modules()
        self.tray_menu(tray_menu)

    def get_enabled_tray_modules(self):
        from openpype_interfaces import ITrayModule

        output = []
        for module in self.modules:
            if module.enabled and isinstance(module, ITrayModule):
                output.append(module)
        return output

    def restart_tray(self):
        if self.tray_manager:
            self.tray_manager.restart()

    def tray_init(self):
        report = {}
        time_start = time.time()
        prev_start_time = time_start
        for module in self.get_enabled_tray_modules():
            try:
                module._tray_manager = self.tray_manager
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
        from openpype_interfaces import ITrayService

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
