import os
import platform
import copy

from openpype.lib import Logger
from openpype.lib.execute import (
    find_executable,
)
from openpype.settings import get_system_settings
from openpype.settings.constants import (
    METADATA_KEYS,
    M_DYNAMIC_KEY_LABEL
)
from .exceptions import (
    ApplicationNotFound,
    ApplictionExecutableNotFound,
)
from .lib import ApplicationLaunchContext


class ApplicationExecutable:
    """Representation of executable loaded from settings."""

    def __init__(self, executable):
        # Try to format executable with environments
        try:
            executable = executable.format(**os.environ)
        except Exception:
            pass

        # On MacOS check if exists path to executable when ends with `.app`
        # - it is common that path will lead to "/Applications/Blender" but
        #   real path is "/Applications/Blender.app"
        if platform.system().lower() == "darwin":
            executable = self.macos_executable_prep(executable)

        self.executable_path = executable

    def __str__(self):
        return self.executable_path

    def __repr__(self):
        return "<{}> {}".format(self.__class__.__name__, self.executable_path)

    @staticmethod
    def macos_executable_prep(executable):
        """Try to find full path to executable file.

        Real executable is stored in '*.app/Contents/MacOS/<executable>'.

        Having path to '*.app' gives ability to read it's plist info and
        use "CFBundleExecutable" key from plist to know what is "executable."

        Plist is stored in '*.app/Contents/Info.plist'.

        This is because some '*.app' directories don't have same permissions
        as real executable.
        """
        # Try to find if there is `.app` file
        if not os.path.exists(executable):
            _executable = executable + ".app"
            if os.path.exists(_executable):
                executable = _executable

        # Try to find real executable if executable has `Contents` subfolder
        contents_dir = os.path.join(executable, "Contents")
        if os.path.exists(contents_dir):
            executable_filename = None
            # Load plist file and check for bundle executable
            plist_filepath = os.path.join(contents_dir, "Info.plist")
            if os.path.exists(plist_filepath):
                import plistlib

                if hasattr(plistlib, "load"):
                    with open(plist_filepath, "rb") as stream:
                        parsed_plist = plistlib.load(stream)
                else:
                    parsed_plist = plistlib.readPlist(plist_filepath)
                executable_filename = parsed_plist.get("CFBundleExecutable")

            if executable_filename:
                executable = os.path.join(
                    contents_dir, "MacOS", executable_filename
                )

        return executable

    def as_args(self):
        return [self.executable_path]

    def _realpath(self):
        """Check if path is valid executable path."""
        # Check for executable in PATH
        result = find_executable(self.executable_path)
        if result is not None:
            return result

        # This is not 100% validation but it is better than remove ability to
        #   launch .bat, .sh or extentionless files
        if os.path.exists(self.executable_path):
            return self.executable_path
        return None

    def exists(self):
        if not self.executable_path:
            return False
        return bool(self._realpath())


class UndefinedApplicationExecutable(ApplicationExecutable):
    """Some applications do not require executable path from settings.

    In that case this class is used to "fake" existing executable.
    """
    def __init__(self):
        pass

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return "<{}>".format(self.__class__.__name__)

    def as_args(self):
        return []

    def exists(self):
        return True


class Application:
    """Hold information about application.

    Object by itself does nothing special.

    Args:
        name (str): Specific version (or variant) of application.
            e.g. "maya2020", "nuke11.3", etc.
        data (dict): Data for the version containing information about
            executables, variant label or if is enabled.
            Only required key is `executables`.
        group (ApplicationGroup): App group object that created the application
            and under which application belongs.
    """

    def __init__(self, name, data, group):
        self.name = name
        self.group = group
        self._data = data

        enabled = False
        if group.enabled:
            enabled = data.get("enabled", True)
        self.enabled = enabled
        self.use_python_2 = data.get("use_python_2", False)

        self.label = data.get("variant_label") or name
        self.full_name = "/".join((group.name, name))

        if group.label:
            full_label = " ".join((group.label, self.label))
        else:
            full_label = self.label
        self.full_label = full_label
        self._environment = data.get("environment") or {}

        arguments = data.get("arguments")
        if isinstance(arguments, dict):
            arguments = arguments.get(platform.system().lower())

        if not arguments:
            arguments = []
        self.arguments = arguments

        if "executables" not in data:
            self.executables = [
                UndefinedApplicationExecutable()
            ]
            return

        _executables = data["executables"]
        if isinstance(_executables, dict):
            _executables = _executables.get(platform.system().lower())

        if not _executables:
            _executables = []

        executables = []
        for executable in _executables:
            executables.append(ApplicationExecutable(executable))

        self.executables = executables

    def __repr__(self):
        return "<{}> - {}".format(self.__class__.__name__, self.full_name)

    @property
    def environment(self):
        return copy.deepcopy(self._environment)

    @property
    def manager(self):
        return self.group.manager

    @property
    def host_name(self):
        return self.group.host_name

    @property
    def icon(self):
        return self.group.icon

    @property
    def is_host(self):
        return self.group.is_host

    def find_executable(self):
        """Try to find existing executable for application.

        Returns (str): Path to executable from `executables` or None if any
            exists.
        """
        for executable in self.executables:
            if executable.exists():
                return executable
        return None

    def launch(self, *args, **kwargs):
        """Launch the application.

        For this purpose is used manager's launch method to keep logic at one
        place.

        Arguments must match with manager's launch method. That's why *args
        **kwargs are used.

        Returns:
            subprocess.Popen: Return executed process as Popen object.
        """
        return self.manager.launch(self.full_name, *args, **kwargs)



class ApplicationGroup:
    """Hold information about application group.

    Application group wraps different versions(variants) of application.
    e.g. "maya" is group and "maya_2020" is variant.

    Group hold `host_name` which is implementation name used in pype. Also
    holds `enabled` if whole app group is enabled or `icon` for application
    icon path in resources.

    Group has also `environment` which hold same environments for all variants.

    Args:
        name (str): Groups' name.
        data (dict): Group defying data loaded from settings.
        manager (ApplicationManager): Manager that created the group.
    """

    def __init__(self, name, data, manager):
        self.name = name
        self.manager = manager
        self._data = data

        self.enabled = data.get("enabled", True)
        self.label = data.get("label") or None
        self.icon = data.get("icon") or None
        self._environment = data.get("environment") or {}

        host_name = data.get("host_name", None)
        self.is_host = host_name is not None
        self.host_name = host_name

        variants = data.get("variants") or {}
        key_label_mapping = variants.pop(M_DYNAMIC_KEY_LABEL, {})
        for variant_name, variant_data in variants.items():
            if variant_name in METADATA_KEYS:
                continue

            if "variant_label" not in variant_data:
                variant_label = key_label_mapping.get(variant_name)
                if variant_label:
                    variant_data["variant_label"] = variant_label

            variants[variant_name] = Application(
                variant_name, variant_data, self
            )

        self.variants = variants

    def __repr__(self):
        return "<{}> - {}".format(self.__class__.__name__, self.name)

    def __iter__(self):
        for variant in self.variants.values():
            yield variant

    @property
    def environment(self):
        return copy.deepcopy(self._environment)



class EnvironmentTool:
    """Hold information about application tool.

    Structure of tool information.

    Args:
        name (str): Name of the tool.
        variant_data (dict): Variant data with environments and
            host and app variant filters.
        group (str): Name of group which wraps tool.
    """

    def __init__(self, name, label, variant_data, group):
        # Backwards compatibility 3.9.1 - 3.9.2
        # - 'variant_data' contained only environments but contain also host
        #   and application variant filters
        host_names = variant_data.get("host_names", [])
        app_variants = variant_data.get("app_variants", [])

        if "environment" in variant_data:
            environment = variant_data["environment"]
        else:
            environment = variant_data

        self.host_names = host_names
        self.app_variants = app_variants
        self.name = name
        self.variant_label = label
        self.label = " ".join((group.label, label))
        self.group = group

        self._environment = environment
        self.full_name = "/".join((group.name, name))

    def __repr__(self):
        return "<{}> - {}".format(self.__class__.__name__, self.full_name)

    @property
    def environment(self):
        return copy.deepcopy(self._environment)

    def is_valid_for_app(self, app):
        """Is tool valid for application.

        Args:
            app (Application): Application for which are prepared environments.
        """
        if self.app_variants and app.full_name not in self.app_variants:
            return False

        if self.host_names and app.host_name not in self.host_names:
            return False
        return True


class EnvironmentToolGroup:
    """Hold information about environment tool group.

    Environment tool group may hold different variants of same tool and set
    environments that are same for all of them.

    e.g. "mtoa" may have different versions but all environments except one
        are same.

    Args:
        name (str): Name of the tool group.
        data (dict): Group's information with it's variants.
        manager (ApplicationManager): Manager that creates the group.
    """

    def __init__(self, name, label, data, manager):
        self.name = name
        self.label = label
        self._data = data
        self.manager = manager
        self._environment = data["environment"]

        variants = data.get("variants") or {}
        label_by_key = variants.pop(M_DYNAMIC_KEY_LABEL, {})
        variants_by_name = {}
        for variant_name, variant_data in variants.items():
            if variant_name in METADATA_KEYS:
                continue

            variant_label = label_by_key.get(variant_name) or variant_name
            tool = EnvironmentTool(
                variant_name, variant_label, variant_data, self
            )
            variants_by_name[variant_name] = tool
        self.variants = variants_by_name

    def __repr__(self):
        return "<{}> - {}".format(self.__class__.__name__, self.name)

    def __iter__(self):
        for variant in self.variants.values():
            yield variant

    @property
    def environment(self):
        return copy.deepcopy(self._environment)


class ApplicationManager:
    """Load applications and tools and store them by their full name.

    Args:
        system_settings (dict): Preloaded system settings. When passed manager
            will always use these values. Gives ability to create manager
            using different settings.
    """

    def __init__(self, system_settings=None):
        self.log = Logger.get_logger(self.__class__.__name__)

        self.app_groups = {}
        self.applications = {}
        self.tool_groups = {}
        self.tools = {}

        self._system_settings = system_settings

        self.refresh()

    def set_system_settings(self, system_settings):
        """Ability to change init system settings.

        This will trigger refresh of manager.
        """
        self._system_settings = system_settings

        self.refresh()

    def refresh(self):
        """Refresh applications from settings."""
        self.app_groups.clear()
        self.applications.clear()
        self.tool_groups.clear()
        self.tools.clear()

        if self._system_settings is not None:
            settings = copy.deepcopy(self._system_settings)
        else:
            settings = get_system_settings(
                clear_metadata=False, exclude_locals=False
            )

        all_app_defs = {}
        # Prepare known applications
        app_defs = settings["applications"]
        additional_apps = {}
        for group_name, variant_defs in app_defs.items():
            if group_name in METADATA_KEYS:
                continue

            if group_name == "additional_apps":
                additional_apps = variant_defs
            else:
                all_app_defs[group_name] = variant_defs

        # Prepare additional applications
        # - First find dynamic keys that can be used as labels of group
        dynamic_keys = {}
        for group_name, variant_defs in additional_apps.items():
            if group_name == M_DYNAMIC_KEY_LABEL:
                dynamic_keys = variant_defs
                break

        # Add additional apps to known applications
        for group_name, variant_defs in additional_apps.items():
            if group_name in METADATA_KEYS:
                continue

            # Determine group label
            label = variant_defs.get("label")
            if not label:
                # Look for label set in dynamic labels
                label = dynamic_keys.get(group_name)
                if not label:
                    label = group_name
                variant_defs["label"] = label

            all_app_defs[group_name] = variant_defs

        for group_name, variant_defs in all_app_defs.items():
            if group_name in METADATA_KEYS:
                continue

            group = ApplicationGroup(group_name, variant_defs, self)
            self.app_groups[group_name] = group
            for app in group:
                self.applications[app.full_name] = app

        tools_definitions = settings["tools"]["tool_groups"]
        tool_label_mapping = tools_definitions.pop(M_DYNAMIC_KEY_LABEL, {})
        for tool_group_name, tool_group_data in tools_definitions.items():
            if not tool_group_name or tool_group_name in METADATA_KEYS:
                continue

            tool_group_label = (
                tool_label_mapping.get(tool_group_name) or tool_group_name
            )
            group = EnvironmentToolGroup(
                tool_group_name, tool_group_label, tool_group_data, self
            )
            self.tool_groups[tool_group_name] = group
            for tool in group:
                self.tools[tool.full_name] = tool

    def find_latest_available_variant_for_group(self, group_name):
        group = self.app_groups.get(group_name)
        if group is None or not group.enabled:
            return None

        output = None
        for _, variant in reversed(sorted(group.variants.items())):
            executable = variant.find_executable()
            if executable:
                output = variant
                break
        return output

    def launch(self, app_name, **data):
        """Launch procedure.

        For host application it's expected to contain "project_name",
        "asset_name" and "task_name".

        Args:
            app_name (str): Name of application that should be launched.
            **data (dict): Any additional data. Data may be used during
                preparation to store objects usable in multiple places.

        Raises:
            ApplicationNotFound: Application was not found by entered
                argument `app_name`.
            ApplictionExecutableNotFound: Executables in application definition
                were not found on this machine.
            ApplicationLaunchFailed: Something important for application launch
                failed. Exception should contain explanation message,
                traceback should not be needed.
        """
        app = self.applications.get(app_name)
        if not app:
            raise ApplicationNotFound(app_name)

        executable = app.find_executable()
        if not executable:
            raise ApplictionExecutableNotFound(app)

        context = ApplicationLaunchContext(
            app, executable, **data
        )
        return context.launch()
