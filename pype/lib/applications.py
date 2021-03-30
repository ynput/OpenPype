import os
import re
import copy
import json
import platform
import getpass
import collections
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
        self.label = data.get("label") or name
        self.icon = data.get("icon") or None
        self._environment = data.get("environment") or {}

        host_name = data.get("host_name", None)
        self.is_host = host_name is not None
        self.host_name = host_name

        variants = data.get("variants") or {}
        for variant_name, variant_data in variants.items():
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


class Application:
    """Hold information about application.

    Object by itself does nothing special.

    Args:
        name (str): Specific version (or variant) of application.
            e.g. "maya2020", "nuke11.3", etc.
        data (dict): Data for the version containing information about
            executables, variant label or if is enabled.
            Only required key is `executables`.
        group (ApplicationGroup): App group object that created the applicaiton
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

        self.label = data.get("variant_label") or name
        self.full_name = "/".join((group.name, name))
        self.full_label = " ".join((group.label, self.label))
        self._environment = data.get("environment") or {}

        _executables = data["executables"]
        if not _executables:
            _executables = []

        elif isinstance(_executables, dict):
            _executables = _executables.get(platform.system().lower()) or []

        _arguments = data["arguments"]
        if not _arguments:
            _arguments = []

        elif isinstance(_arguments, dict):
            _arguments = _arguments.get(platform.system().lower()) or []

        executables = []
        for executable in _executables:
            executables.append(ApplicationExecutable(executable))

        self.executables = executables
        self.arguments = _arguments

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
        return self.manager.launch(self.name, *args, **kwargs)


class ApplicationManager:
    def __init__(self):
        self.log = PypeLogger().get_logger(self.__class__.__name__)

        self.app_groups = {}
        self.applications = {}
        self.tools = {}

        self.refresh()

    def refresh(self):
        """Refresh applications from settings."""
        self.app_groups.clear()
        self.applications.clear()
        self.tools.clear()

        settings = get_system_settings()

        app_defs = settings["applications"]
        for group_name, variant_defs in app_defs.items():
            group = ApplicationGroup(group_name, variant_defs, self)
            self.app_groups[group_name] = group
            for app in group:
                # TODO This should be replaced with `full_name` in future
                self.applications[app.name] = app

        tools_definitions = settings["tools"]["tool_groups"]
        for tool_group_name, tool_group_data in tools_definitions.items():
            tool_variants = tool_group_data.get("variants") or {}
            for tool_name, tool_data in tool_variants.items():
                tool = ApplicationTool(tool_name, tool_group_name)
                if tool.full_name in self.tools:
                    self.log.warning((
                        "Duplicated tool name in settings \"{}\""
                    ).format(tool.full_name))
                self.tools[tool.full_name] = tool

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
    """

    def __init__(self, tool_name, group_name):
        self.name = tool_name
        self.group_name = group_name

    @property
    def full_name(self):
        return "/".join((self.group_name, self.name))


class ApplicationExecutable:
    def __init__(self, executable):
        self.executable_path = executable

    def __str__(self):
        return self.executable_path

    def __repr__(self):
        return "<{}> {}".format(self.__class__.__name__, self.executable_path)

    def as_args(self):
        return [self.executable_path]

    def _realpath(self):
        """Check if path is valid executable path."""
        # Check for executable in PATH
        result = distutils.spawn.find_executable(self.executable_path)
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
        self.launch_args.extend(application.arguments)

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
            ["hooks"],
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

            modules, _crashed = modules_from_path(path)
            for _filepath, module in modules:
                all_classes["pre"].extend(
                    classes_from_module(PreLaunchHook, module)
                )
                all_classes["post"].extend(
                    classes_from_module(PostLaunchHook, module)
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


class MissingRequiredKey(KeyError):
    pass


class EnvironmentPrepData(dict):
    """Helper dictionary for storin temp data during environment prep.

    Args:
        data (dict): Data must contain required keys.
    """
    required_keys = (
        "project_doc", "asset_doc", "task_name", "app", "anatomy"
    )

    def __init__(self, data):
        for key in self.required_keys:
            if key not in data:
                raise MissingRequiredKey(key)

        if not data.get("log"):
            data["log"] = get_logger()

        if data.get("env") is None:
            data["env"] = os.environ.copy()

        if data.get("settings_env") is None:
            data["settings_env"] = get_environments()

        super(EnvironmentPrepData, self).__init__(data)


def get_app_environments_for_context(
    project_name, asset_name, task_name, app_name, env=None
):
    """Prepare environment variables by context.
    Args:
        project_name (str): Name of project.
        asset_name (str): Name of asset.
        task_name (str): Name of task.
        app_name (str): Name of application that is launched and can be found
            by ApplicationManager.
        env (dict): Initial environment variables. `os.environ` is used when
            not passed.

    Returns:
        dict: Environments for passed context and application.
    """
    from avalon.api import AvalonMongoDB

    # Avalon database connection
    dbcon = AvalonMongoDB()
    dbcon.Session["AVALON_PROJECT"] = project_name
    dbcon.install()

    # Project document
    project_doc = dbcon.find_one({"type": "project"})
    asset_doc = dbcon.find_one({
        "type": "asset",
        "name": asset_name
    })

    # Prepare app object which can be obtained only from ApplciationManager
    app_manager = ApplicationManager()
    app = app_manager.applications[app_name]

    # Project's anatomy
    anatomy = Anatomy(project_name)

    data = EnvironmentPrepData({
        "project_name": project_name,
        "asset_name": asset_name,
        "task_name": task_name,
        "app_name": app_name,
        "app": app,

        "dbcon": dbcon,
        "project_doc": project_doc,
        "asset_doc": asset_doc,

        "anatomy": anatomy,

        "env": env
    })

    prepare_host_environments(data)
    prepare_context_environments(data)

    # Discard avalon connection
    dbcon.uninstall()

    return data["env"]


def _merge_env(env, current_env):
    """Modified function(merge) from acre module."""
    import acre

    result = current_env.copy()
    for key, value in env.items():
        # Keep missing keys by not filling `missing` kwarg
        value = acre.lib.partial_format(value, data=current_env)
        result[key] = value
    return result


def prepare_host_environments(data):
    """Modify launch environments based on launched app and context.

    Args:
        data (EnvironmentPrepData): Dictionary where result and intermediate
            result will be stored.
    """
    import acre

    app = data["app"]
    log = data["log"]

    # Keys for getting environments
    env_keys = [app.app_group, app.app_name]

    asset_doc = data.get("asset_doc")
    if asset_doc:
        # Add tools environments
        for key in asset_doc["data"].get("tools_env") or []:
            tool = app.manager.tools.get(key)
            if tool:
                if tool.group_name not in env_keys:
                    env_keys.append(tool.group_name)

                if tool.name not in env_keys:
                    env_keys.append(tool.name)

    log.debug(
        "Finding environment groups for keys: {}".format(env_keys)
    )

    settings_env = data["settings_env"]
    env_values = {}
    for env_key in env_keys:
        _env_values = settings_env.get(env_key)
        if not _env_values:
            continue

        # Choose right platform
        tool_env = acre.parse(_env_values)
        # Merge dictionaries
        env_values = _merge_env(tool_env, env_values)

    final_env = _merge_env(acre.compute(env_values), data["env"])

    # Update env
    data["env"].update(final_env)


def apply_project_environments_value(project_name, env, project_settings=None):
    """Apply project specific environments on passed environments.

    Args:
        project_name (str): Name of project for which environemnts should be
            received.
        env (dict): Environment values on which project specific environments
            will be applied.
        project_settings (dict): Project settings for passed project name.
            Optional if project settings are already prepared.

    Raises:
        KeyError: If project settings do not contain keys for project specific
            environments.
    """
    import acre

    if project_settings is None:
        project_settings = get_project_settings(project_name)

    env_value = project_settings["global"]["project_environments"]
    if not env_value:
        return env
    parsed = acre.parse(env_value)
    return _merge_env(parsed, env)


def prepare_context_environments(data):
    """Modify launch environemnts with context data for launched host.

    Args:
        data (EnvironmentPrepData): Dictionary where result and intermediate
            result will be stored.
    """
    # Context environments
    log = data["log"]

    project_doc = data["project_doc"]
    asset_doc = data["asset_doc"]
    task_name = data["task_name"]
    if (
        not project_doc
        or not asset_doc
        or not task_name
    ):
        log.info(
            "Skipping context environments preparation."
            " Launch context does not contain required data."
        )
        return

    # Load project specific environments
    project_name = project_doc["name"]
    data["env"] = apply_project_environments_value(
        project_name, data["env"]
    )

    app = data["app"]
    workdir_data = get_workdir_data(
        project_doc, asset_doc, task_name, app.host_name
    )
    data["workdir_data"] = workdir_data

    anatomy = data["anatomy"]

    try:
        workdir = get_workdir_with_workdir_data(workdir_data, anatomy)
        if not os.path.exists(workdir):
            log.debug(
                "Creating workdir folder: \"{}\"".format(workdir)
            )
            os.makedirs(workdir)

    except Exception as exc:
        raise ApplicationLaunchFailed(
            "Error in anatomy.format: {}".format(str(exc))
        )

    context_env = {
        "AVALON_PROJECT": project_doc["name"],
        "AVALON_ASSET": asset_doc["name"],
        "AVALON_TASK": task_name,
        "AVALON_APP": app.host_name,
        "AVALON_APP_NAME": app.app_name,
        "AVALON_WORKDIR": workdir
    }
    log.debug(
        "Context environemnts set:\n{}".format(
            json.dumps(context_env, indent=4)
        )
    )
    data["env"].update(context_env)

    _prepare_last_workfile(data, workdir)


def _prepare_last_workfile(data, workdir):
    """last workfile workflow preparation.

    Function check if should care about last workfile workflow and tries
    to find the last workfile. Both information are stored to `data` and
    environments.

    Last workfile is filled always (with version 1) even if any workfile
    exists yet.

    Args:
        data (EnvironmentPrepData): Dictionary where result and intermediate
            result will be stored.
        workdir (str): Path to folder where workfiles should be stored.
    """
    import avalon.api

    log = data["log"]
    _workdir_data = data.get("workdir_data")
    if not _workdir_data:
        log.info(
            "Skipping last workfile preparation."
            " Key `workdir_data` not filled."
        )
        return

    app = data["app"]
    workdir_data = copy.deepcopy(_workdir_data)
    project_name = data["project_name"]
    task_name = data["task_name"]
    start_last_workfile = should_start_last_workfile(
        project_name, app.host_name, task_name
    )
    data["start_last_workfile"] = start_last_workfile

    # Store boolean as "0"(False) or "1"(True)
    data["env"]["AVALON_OPEN_LAST_WORKFILE"] = (
        str(int(bool(start_last_workfile)))
    )

    _sub_msg = "" if start_last_workfile else " not"
    log.debug(
        "Last workfile should{} be opened on start.".format(_sub_msg)
    )

    # Last workfile path
    last_workfile_path = ""
    extensions = avalon.api.HOST_WORKFILE_EXTENSIONS.get(
        app.host_name
    )
    if extensions:
        anatomy = data["anatomy"]
        # Find last workfile
        file_template = anatomy.templates["work"]["file"]
        workdir_data.update({
            "version": 1,
            "user": os.environ.get("PYPE_USERNAME") or getpass.getuser(),
            "ext": extensions[0]
        })

        last_workfile_path = avalon.api.last_workfile(
            workdir, file_template, workdir_data, extensions, True
        )

    if os.path.exists(last_workfile_path):
        log.debug((
            "Workfiles for launch context does not exists"
            " yet but path will be set."
        ))
    log.debug(
        "Setting last workfile path: {}".format(last_workfile_path)
    )

    data["env"]["AVALON_LAST_WORKFILE"] = last_workfile_path
    data["last_workfile_path"] = last_workfile_path


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
