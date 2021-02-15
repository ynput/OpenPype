import os
import re
import copy
import json
import platform
import getpass
import inspect
import subprocess
import distutils.spawn
from abc import ABCMeta, abstractmethod

import six

from pype.settings import (
    get_system_settings,
    get_project_settings,
    get_environments
)
from . import (
    PypeLogger,
    Anatomy
)
from .avalon_context import (
    get_workdir_data,
    get_workdir_with_workdir_data
)

from .python_module_tools import (
    modules_from_path,
    classes_from_module
)


_logger = None


def get_logger():
    """Global lib.applications logger getter."""
    global _logger
    if _logger is None:
        _logger = PypeLogger.get_logger(__name__)
    return _logger


class ApplicationNotFound(Exception):
    """Application was not found in ApplicationManager by name."""

    def __init__(self, app_name):
        self.app_name = app_name
        super(ApplicationNotFound, self).__init__(
            "Application \"{}\" was not found.".format(app_name)
        )


class ApplictionExecutableNotFound(Exception):
    """Defined executable paths are not available on the machine."""

    def __init__(self, application):
        self.application = application
        details = None
        if not application.executables:
            msg = (
                "Executable paths for application \"{}\"({}) are not set."
            )
        else:
            msg = (
                "Defined executable paths for application \"{}\"({})"
                " are not available on this machine."
            )
            details = "Defined paths:"
            for executable in application.executables:
                details += "\n- " + executable.executable_path

        self.msg = msg.format(application.full_label, application.app_name)
        self.details = details

        exc_mgs = str(self.msg)
        if details:
            # Is good idea to pass new line symbol to exception message?
            exc_mgs += "\n" + details
        self.exc_msg = exc_mgs
        super(ApplictionExecutableNotFound, self).__init__(exc_mgs)


class ApplicationLaunchFailed(Exception):
    """Application launch failed due to known reason.

    Message should be self explanatory as traceback won't be shown.
    """
    pass


class ApplicationManager:
    def __init__(self):
        self.log = PypeLogger().get_logger(self.__class__.__name__)

        self.applications = {}
        self.tools = {}

        self.refresh()

    def refresh(self):
        """Refresh applications from settings."""
        settings = get_system_settings()

        hosts_definitions = settings["applications"]
        for app_group, variant_definitions in hosts_definitions.items():
            enabled = variant_definitions["enabled"]
            label = variant_definitions.get("label") or app_group
            variants = variant_definitions.get("variants") or {}
            icon = variant_definitions.get("icon")
            group_host_name = variant_definitions.get("host_name") or None
            for app_name, app_data in variants.items():
                if app_name in self.applications:
                    raise AssertionError((
                        "BUG: Duplicated application name in settings \"{}\""
                    ).format(app_name))

                # If host is disabled then disable all variants
                if not enabled:
                    app_data["enabled"] = enabled

                # Pass label from host definition
                if not app_data.get("label"):
                    app_data["label"] = label

                if not app_data.get("icon"):
                    app_data["icon"] = icon

                host_name = app_data.get("host_name") or group_host_name

                app_data["is_host"] = host_name is not None

                self.applications[app_name] = Application(
                    app_group, app_name, host_name, app_data, self
                )

        tools_definitions = settings["tools"]
        for tool_group_name, tool_group_data in tools_definitions.items():
            enabled = tool_group_data.get("enabled", True)
            tool_variants = tool_group_data.get("variants") or {}
            for tool_name, tool_data in tool_variants.items():
                if tool_name in self.tools:
                    self.log.warning((
                        "Duplicated tool name in settings \"{}\""
                    ).format(tool_name))

                _enabled = tool_data.get("enabled", enabled)
                self.tools[tool_name] = ApplicationTool(
                    tool_name, tool_group_name, _enabled
                )

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
        # TODO pass context through launch hooks
        return context.launch()


class ApplicationTool:
    """Hold information about application tool.

    Structure of tool information.

    Args:
        tool_name (str): Name of the tool.
        group_name (str): Name of group which wraps tool.
        enabled (bool): Is tool enabled by studio.
    """

    def __init__(self, tool_name, group_name, enabled):
        self.name = tool_name
        self.group_name = group_name
        self.enabled = enabled

    def __bool__(self):
        return self.enabled


class ApplicationExecutable:
    def __init__(self, executable):
        default_launch_args = []
        executable_path = None
        if isinstance(executable, str):
            executable_path = executable

        elif isinstance(executable, list):
            for arg in executable:
                if arg:
                    if executable_path is None:
                        executable_path = arg
                    else:
                        default_launch_args.append(arg)

        self.executable_path = executable_path
        self.default_launch_args = default_launch_args

    def __iter__(self):
        yield distutils.spawn.find_executable(self.executable_path)
        for arg in self.default_launch_args:
            yield arg

    def __str__(self):
        return self.executable_path

    def as_args(self):
        return list(self)

    def exists(self):
        if not self.executable_path:
            return False
        return bool(distutils.spawn.find_executable(self.executable_path))


class Application:
    """Hold information about application.

    Object by itself does nothing special.

    Args:
        app_group (str): App group name.
            e.g. "maya", "nuke", "photoshop", etc.
        app_name (str): Specific version (or variant) of host.
            e.g. "maya2020", "nuke11.3", etc.
        host_name (str): Name of host implementation.
        app_data (dict): Data for the version containing information about
            executables, label, variant label, icon or if is enabled.
            Only required key is `executables`.
        manager (ApplicationManager): Application manager that created object.
    """

    def __init__(self, app_group, app_name, host_name, app_data, manager):
        self.app_group = app_group
        self.app_name = app_name
        self.host_name = host_name
        self.app_data = app_data
        self.manager = manager

        self.label = app_data.get("label") or app_name
        self.variant_label = app_data.get("variant_label") or None
        self.icon = app_data.get("icon") or None
        self.enabled = app_data.get("enabled", True)
        self.is_host = app_data.get("is_host", False)

        _executables = app_data["executables"]
        if not _executables:
            _executables = []

        elif isinstance(_executables, dict):
            _executables = _executables.get(platform.system().lower()) or []

        executables = []
        for executable in _executables:
            executables.append(ApplicationExecutable(executable))

        self.executables = executables

    @property
    def full_label(self):
        """Full label of application.

        Concatenate `label` and `variant_label` attributes if `variant_label`
        is set.
        """
        if self.variant_label:
            return "{} {}".format(self.label, self.variant_label)
        return str(self.label)

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
        return self.manager.launch(self.app_name, *args, **kwargs)


@six.add_metaclass(ABCMeta)
class LaunchHook:
    """Abstract base class of launch hook."""
    # Order of prelaunch hook, will be executed as last if set to None.
    order = None
    # List of host implementations, skipped if empty.
    hosts = []
    # List of application groups
    app_groups = []
    # List of specific application names
    app_names = []
    # List of platform availability, skipped if empty.
    platforms = []

    def __init__(self, launch_context):
        """Constructor of launch hook.

        Always should be called
        """
        self.log = PypeLogger().get_logger(self.__class__.__name__)

        self.launch_context = launch_context

        is_valid = self.class_validation(launch_context)
        if is_valid:
            is_valid = self.validate()

        self.is_valid = is_valid

    @classmethod
    def class_validation(cls, launch_context):
        """Validation of class attributes by launch context.

        Args:
            launch_context (ApplicationLaunchContext): Context of launching
                application.

        Returns:
            bool: Is launch hook valid for the context by class attributes.
        """
        if cls.platforms:
            low_platforms = tuple(
                _platform.lower()
                for _platform in cls.platforms
            )
            if platform.system().lower() not in low_platforms:
                return False

        if cls.hosts:
            if launch_context.host_name not in cls.hosts:
                return False

        if cls.app_groups:
            if launch_context.app_group not in cls.app_groups:
                return False

        if cls.app_names:
            if launch_context.app_name not in cls.app_names:
                return False

        return True

    @property
    def data(self):
        return self.launch_context.data

    @property
    def application(self):
        return getattr(self.launch_context, "application", None)

    @property
    def manager(self):
        return getattr(self.application, "manager", None)

    @property
    def host_name(self):
        return getattr(self.application, "host_name", None)

    @property
    def app_group(self):
        return getattr(self.application, "app_group", None)

    @property
    def app_name(self):
        return getattr(self.application, "app_name", None)

    def validate(self):
        """Optional validation of launch hook on initialization.

        Returns:
            bool: Hook is valid (True) or invalid (False).
        """
        # QUESTION Not sure if this method has any usable potential.
        # - maybe result can be based on settings
        return True

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Abstract execute method where logic of hook is."""
        pass


class PreLaunchHook(LaunchHook):
    """Abstract class of prelaunch hook.

    This launch hook will be processed before application is launched.

    If any exception will happen during processing the application won't be
    launched.
    """


class PostLaunchHook(LaunchHook):
    """Abstract class of postlaunch hook.

    This launch hook will be processed after application is launched.

    Nothing will happen if any exception will happen during processing. And
    processing of other postlaunch hooks won't stop either.
    """


class ApplicationLaunchContext:
    """Context of launching application.

    Main purpose of context is to prepare launch arguments and keword arguments
    for new process. Most important part of keyword arguments preparations
    are environment variables.

    During the whole process is possible to use `data` attribute to store
    object usable in multiple places.

    Launch arguments are strings in list. It is possible to "chain" argument
    when order of them matters. That is possible to do with adding list where
    order is right and should not change.
    NOTE: This is recommendation, not requirement.
    e.g.: `["nuke.exe", "--NukeX"]` -> In this case any part of process may
    insert argument between `nuke.exe` and `--NukeX`. To keep them together
    it is better to wrap them in another list: `[["nuke.exe", "--NukeX"]]`.

    Args:
        application (Application): Application definition.
        executable (ApplicationExecutable): Object with path to executable.
        **data (dict): Any additional data. Data may be used during
            preparation to store objects usable in multiple places.
    """

    def __init__(self, application, executable, **data):
        # Application object
        self.application = application

        # Logger
        logger_name = "{}-{}".format(self.__class__.__name__, self.app_name)
        self.log = PypeLogger().get_logger(logger_name)

        self.executable = executable

        self.data = dict(data)

        # Load settings if were not passed in data
        settings_env = self.data.get("settings_env")
        if settings_env is None:
            settings_env = get_environments()
            self.data["settings_env"] = settings_env

        # subprocess.Popen launch arguments (first argument in constructor)
        self.launch_args = executable.as_args()

        # Handle launch environemtns
        env = self.data.pop("env", None)
        if env is not None and not isinstance(env, dict):
            self.log.warning((
                "Passed `env` kwarg has invalid type: {}. Expected: `dict`."
                " Using `os.environ` instead."
            ).format(str(type(env))))
            env = None

        if env is None:
            env = os.environ

        # subprocess.Popen keyword arguments
        self.kwargs = {
            "env": {
                key: str(value)
                for key, value in env.items()
            }
        }

        if platform.system().lower() == "windows":
            # Detach new process from currently running process on Windows
            flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
            )
            self.kwargs["creationflags"] = flags

        self.prelaunch_hooks = None
        self.postlaunch_hooks = None

        self.process = None

    @property
    def env(self):
        if (
            "env" not in self.kwargs
            or self.kwargs["env"] is None
        ):
            self.kwargs["env"] = {}
        return self.kwargs["env"]

    @env.setter
    def env(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "'env' attribute expect 'dict' object. Got: {}".format(
                    str(type(value))
                )
            )
        self.kwargs["env"] = value

    def paths_to_launch_hooks(self):
        """Directory paths where to look for launch hooks."""
        # This method has potential to be part of application manager (maybe).
        paths = []

        # TODO load additional studio paths from settings
        import pype
        pype_dir = os.path.dirname(os.path.abspath(pype.__file__))

        # --- START: Backwards compatibility ---
        hooks_dir = os.path.join(pype_dir, "hooks")

        subfolder_names = ["global", self.host_name]
        for subfolder_name in subfolder_names:
            path = os.path.join(hooks_dir, subfolder_name)
            if (
                os.path.exists(path)
                and os.path.isdir(path)
                and path not in paths
            ):
                paths.append(path)
        # --- END: Backwards compatibility ---

        subfolders_list = (
            ("hooks", "global"),
            ("hosts", self.host_name, "hooks")
        )
        for subfolders in subfolders_list:
            path = os.path.join(pype_dir, *subfolders)
            if (
                os.path.exists(path)
                and os.path.isdir(path)
                and path not in paths
            ):
                paths.append(path)

        # Load modules paths
        from pype.modules import ModulesManager

        manager = ModulesManager()
        paths.extend(manager.collect_launch_hook_paths())

        return paths

    def discover_launch_hooks(self, force=False):
        """Load and prepare launch hooks."""
        if (
            self.prelaunch_hooks is not None
            or self.postlaunch_hooks is not None
        ):
            if not force:
                self.log.info("Launch hooks were already discovered.")
                return

            self.prelaunch_hooks.clear()
            self.postlaunch_hooks.clear()

        self.log.debug("Discovery of launch hooks started.")

        paths = self.paths_to_launch_hooks()
        self.log.debug("Paths where will look for launch hooks:{}".format(
            "\n- ".join(paths)
        ))

        all_classes = {
            "pre": [],
            "post": []
        }
        for path in paths:
            if not os.path.exists(path):
                self.log.info(
                    "Path to launch hooks does not exists: \"{}\"".format(path)
                )
                continue

            modules = modules_from_path(path)
            for _module in modules:
                all_classes["pre"].extend(
                    classes_from_module(PreLaunchHook, _module)
                )
                all_classes["post"].extend(
                    classes_from_module(PostLaunchHook, _module)
                )

        for launch_type, classes in all_classes.items():
            hooks_with_order = []
            hooks_without_order = []
            for klass in classes:
                try:
                    hook = klass(self)
                    if not hook.is_valid:
                        self.log.debug(
                            "Hook is not valid for curent launch context."
                        )
                        continue

                    if inspect.isabstract(hook):
                        self.log.debug("Skipped abstract hook: {}".format(
                            str(hook)
                        ))
                        continue

                    # Separate hooks by pre/post class
                    if hook.order is None:
                        hooks_without_order.append(hook)
                    else:
                        hooks_with_order.append(hook)

                except Exception:
                    self.log.warning(
                        "Initialization of hook failed. {}".format(str(klass)),
                        exc_info=True
                    )

            # Sort hooks with order by order
            ordered_hooks = list(sorted(
                hooks_with_order, key=lambda obj: obj.order
            ))
            # Extend ordered hooks with hooks without defined order
            ordered_hooks.extend(hooks_without_order)

            if launch_type == "pre":
                self.prelaunch_hooks = ordered_hooks
            else:
                self.postlaunch_hooks = ordered_hooks

        self.log.debug("Found {} prelaunch and {} postlaunch hooks.".format(
            len(self.prelaunch_hooks), len(self.postlaunch_hooks)
        ))

    @property
    def app_name(self):
        return self.application.app_name

    @property
    def host_name(self):
        return self.application.host_name

    @property
    def app_group(self):
        return self.application.app_group

    @property
    def manager(self):
        return self.application.manager

    def launch(self):
        """Collect data for new process and then create it.

        This method must not be executed more than once.

        Returns:
            subprocess.Popen: Created process as Popen object.
        """
        if self.process is not None:
            self.log.warning("Application was already launched.")
            return

        # Discover launch hooks
        self.discover_launch_hooks()

        # Execute prelaunch hooks
        for prelaunch_hook in self.prelaunch_hooks:
            self.log.debug("Executing prelaunch hook: {}".format(
                str(prelaunch_hook.__class__.__name__)
            ))
            prelaunch_hook.execute()

        self.log.debug("All prelaunch hook executed. Starting new process.")

        # Prepare subprocess args
        args = self.clear_launch_args(self.launch_args)
        self.log.debug(
            "Launching \"{}\" with args ({}): {}".format(
                self.app_name, len(args), args
            )
        )
        # Run process
        self.process = subprocess.Popen(args, **self.kwargs)

        # Process post launch hooks
        for postlaunch_hook in self.postlaunch_hooks:
            self.log.debug("Executing postlaunch hook: {}".format(
                str(postlaunch_hook.__class__.__name__)
            ))

            # TODO how to handle errors?
            # - store to variable to let them accesible?
            try:
                postlaunch_hook.execute()

            except Exception:
                self.log.warning(
                    "After launch procedures were not successful.",
                    exc_info=True
                )

        self.log.debug("Launch of {} finished.".format(self.app_name))

        return self.process

    @staticmethod
    def clear_launch_args(args):
        """Collect launch arguments to final order.

        Launch argument should be list that may contain another lists this
        function will upack inner lists and keep ordering.

        ```
        # source
        [ [ arg1, [ arg2, arg3 ] ], arg4, [arg5, arg6]]
        # result
        [ arg1, arg2, arg3, arg4, arg5, arg6]

        Args:
            args (list): Source arguments in list may contain inner lists.

        Return:
            list: Unpacked arguments.
        """
        while True:
            all_cleared = True
            new_args = []
            for arg in args:
                if isinstance(arg, (list, tuple, set)):
                    all_cleared = False
                    for _arg in arg:
                        new_args.append(_arg)
                else:
                    new_args.append(arg)
            args = new_args

            if all_cleared:
                break
        return args


def should_start_last_workfile(
    project_name, host_name, task_name, default_output=False
):
    """Define if host should start last version workfile if possible.

    Default output is `False`. Can be overriden with environment variable
    `AVALON_OPEN_LAST_WORKFILE`, valid values without case sensitivity are
    `"0", "1", "true", "false", "yes", "no"`.

    Args:
        project_name (str): Name of project.
        host_name (str): Name of host which is launched. In avalon's
            application context it's value stored in app definition under
            key `"application_dir"`. Is not case sensitive.
        task_name (str): Name of task which is used for launching the host.
            Task name is not case sensitive.

    Returns:
        bool: True if host should start workfile.

    """

    project_settings = get_project_settings(project_name)
    startup_presets = (
        project_settings
        ["global"]
        ["tools"]
        ["Workfiles"]
        ["last_workfile_on_startup"]
    )

    if not startup_presets:
        return default_output

    host_name_lowered = host_name.lower()
    task_name_lowered = task_name.lower()

    max_points = 2
    matching_points = -1
    matching_item = None
    for item in startup_presets:
        hosts = item.get("hosts") or tuple()
        tasks = item.get("tasks") or tuple()

        hosts_lowered = tuple(_host_name.lower() for _host_name in hosts)
        # Skip item if has set hosts and current host is not in
        if hosts_lowered and host_name_lowered not in hosts_lowered:
            continue

        tasks_lowered = tuple(_task_name.lower() for _task_name in tasks)
        # Skip item if has set tasks and current task is not in
        if tasks_lowered:
            task_match = False
            for task_regex in compile_list_of_regexes(tasks_lowered):
                if re.match(task_regex, task_name_lowered):
                    task_match = True
                    break

            if not task_match:
                continue

        points = int(bool(hosts_lowered)) + int(bool(tasks_lowered))
        if points > matching_points:
            matching_item = item
            matching_points = points

        if matching_points == max_points:
            break

    if matching_item is not None:
        output = matching_item.get("enabled")
        if output is None:
            output = default_output
        return output
    return default_output


def compile_list_of_regexes(in_list):
    """Convert strings in entered list to compiled regex objects."""
    regexes = list()
    if not in_list:
        return regexes

    for item in in_list:
        if not item:
            continue
        try:
            regexes.append(re.compile(item))
        except TypeError:
            print((
                "Invalid type \"{}\" value \"{}\"."
                " Expected string based object. Skipping."
            ).format(str(type(item)), str(item)))
    return regexes
