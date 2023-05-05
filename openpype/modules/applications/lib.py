import os
import sys
import platform
import subprocess
import inspect
import json
import tempfile

import acre
import six

from openpype import PACKAGE_DIR as OPENPYPE_DIR
from openpype.modules import ModulesManager
from openpype.settings import get_system_settings
from openpype.lib import Logger
from openpype.lib.execute import (
    get_linux_launcher_args
)
# Use direct import because of possible difference in classes
#   for discovery ('openpype.modules' vs. 'openpype_modules')
# - did work in tray, did not work e.g. in ftrack
from openpype.modules.applications.hook import discover_launch_hooks
from .exceptions import MissingRequiredKey
from .constants import DEFAULT_ENV_SUBGROUP, PLATFORM_NAMES


def merge_env(env, current_env):
    """Modified function(merge) from acre module."""

    result = current_env.copy()
    for key, value in env.items():
        # Keep missing keys by not filling `missing` kwarg
        value = acre.lib.partial_format(value, data=current_env)
        result[key] = value
    return result


def parse_environments(env_data, env_group=None, platform_name=None):
    """Parse environment values from settings byt group and platform.

    Data may contain up to 2 hierarchical levels of dictionaries. At the end
    of the last level must be string or list. List is joined using platform
    specific joiner (';' for windows and ':' for linux and mac).

    Hierarchical levels can contain keys for subgroups and platform name.
    Platform specific values must be always last level of dictionary. Platform
    names are "windows" (MS Windows), "linux" (any linux distribution) and
    "darwin" (any MacOS distribution).

    Subgroups are helpers added mainly for standard and on farm usage. Farm
    may require different environments for e.g. licence related values or
    plugins. Default subgroup is "standard".

    Examples:
    ```
    {
        # Unchanged value
        "ENV_KEY1": "value",
        # Empty values are kept (unset environment variable)
        "ENV_KEY2": "",

        # Join list values with ':' or ';'
        "ENV_KEY3": ["value1", "value2"],

        # Environment groups
        "ENV_KEY4": {
            "standard": "DEMO_SERVER_URL",
            "farm": "LICENCE_SERVER_URL"
        },

        # Platform specific (and only for windows and mac)
        "ENV_KEY5": {
            "windows": "windows value",
            "darwin": ["value 1", "value 2"]
        },

        # Environment groups and platform combination
        "ENV_KEY6": {
            "farm": "FARM_VALUE",
            "standard": {
                "windows": ["value1", "value2"],
                "linux": "value1",
                "darwin": ""
            }
        }
    }
    ```
    """
    output = {}
    if not env_data:
        return output

    if not env_group:
        env_group = DEFAULT_ENV_SUBGROUP

    if not platform_name:
        platform_name = platform.system().lower()

    for key, value in env_data.items():
        if isinstance(value, dict):
            # Look if any key is platform key
            #   - expect that represents environment group if does not contain
            #   platform keys
            if not PLATFORM_NAMES.intersection(set(value.keys())):
                # Skip the key if group is not available
                if env_group not in value:
                    continue
                value = value[env_group]

        # Check again if value is dictionary
        #   - this time there should be only platform keys
        if isinstance(value, dict):
            value = value.get(platform_name)

        # Check if value is list and join it's values
        # QUESTION Should empty values be skipped?
        if isinstance(value, (list, tuple)):
            value = os.pathsep.join(value)

        # Set key to output if value is string
        if isinstance(value, six.string_types):
            output[key] = value
    return output


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
            data["log"] = Logger.get_logger(__name__)

        if data.get("env") is None:
            data["env"] = os.environ.copy()

        if "system_settings" not in data:
            data["system_settings"] = get_system_settings()

        super(EnvironmentPrepData, self).__init__(data)


class ApplicationLaunchContext:
    """Context of launching application.

    Main purpose of context is to prepare launch arguments and keyword arguments
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

    def __init__(self, application, executable, env_group=None, **data):
        # Application object
        self.application = application

        self.modules_manager = ModulesManager()

        # Logger
        logger_name = "{}-{}".format(self.__class__.__name__,
                                     self.application.full_name)
        self.log = Logger.get_logger(logger_name)

        self.executable = executable

        if env_group is None:
            env_group = DEFAULT_ENV_SUBGROUP

        self.env_group = env_group

        self.data = dict(data)

        # subprocess.Popen launch arguments (first argument in constructor)
        self.launch_args = executable.as_args()
        self.launch_args.extend(application.arguments)
        if self.data.get("app_args"):
            self.launch_args.extend(self.data.pop("app_args"))

        # Handle launch environemtns
        src_env = self.data.pop("env", None)
        if src_env is not None and not isinstance(src_env, dict):
            self.log.warning((
                "Passed `env` kwarg has invalid type: {}. Expected: `dict`."
                " Using `os.environ` instead."
            ).format(str(type(src_env))))
            src_env = None

        if src_env is None:
            src_env = os.environ

        ignored_env = {"QT_API", }
        env = {
            key: str(value)
            for key, value in src_env.items()
            if key not in ignored_env
        }
        # subprocess.Popen keyword arguments
        self.kwargs = {"env": env}

        if platform.system().lower() == "windows":
            # Detach new process from currently running process on Windows
            flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
            )
            self.kwargs["creationflags"] = flags

        if not sys.stdout:
            self.kwargs["stdout"] = subprocess.DEVNULL
            self.kwargs["stderr"] = subprocess.DEVNULL

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

    def _collect_addons_launch_hook_paths(self):
        """Helper to collect application launch hooks from addons.

        Module have to have implemented 'get_launch_hook_paths' method which
        can expect application as argument or nothing.

        Returns:
            List[str]: Paths to launch hook directories.
        """

        expected_types = (list, tuple, set)

        output = []
        for module in self.modules_manager.get_enabled_modules():
            # Skip module if does not have implemented 'get_launch_hook_paths'
            func = getattr(module, "get_launch_hook_paths", None)
            if func is None:
                continue

            func = module.get_launch_hook_paths
            if hasattr(inspect, "signature"):
                sig = inspect.signature(func)
                expect_args = len(sig.parameters) > 0
            else:
                expect_args = len(inspect.getargspec(func)[0]) > 0

            # Pass application argument if method expect it.
            try:
                if expect_args:
                    hook_paths = func(self.application)
                else:
                    hook_paths = func()
            except Exception:
                self.log.warning(
                    "Failed to call 'get_launch_hook_paths'",
                    exc_info=True
                )
                continue

            if not hook_paths:
                continue

            # Convert string to list
            if isinstance(hook_paths, six.string_types):
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

    def paths_to_launch_hooks(self):
        """Directory paths where to look for launch hooks."""
        # This method has potential to be part of application manager (maybe).
        paths = []

        # TODO load additional studio paths from settings
        global_hooks_dir = os.path.join(OPENPYPE_DIR, "hooks")

        hooks_dirs = [
            global_hooks_dir
        ]
        if self.host_name:
            # If host requires launch hooks and is module then launch hooks
            #   should be collected using 'collect_launch_hook_paths'
            #   - module have to implement 'get_launch_hook_paths'
            host_module = self.modules_manager.get_host_module(self.host_name)
            if not host_module:
                hooks_dirs.append(os.path.join(
                    OPENPYPE_DIR, "hosts", self.host_name, "hooks"
                ))

        for path in hooks_dirs:
            if (
                os.path.exists(path)
                and os.path.isdir(path)
                and path not in paths
            ):
                paths.append(path)

        # Load modules paths
        paths.extend(self._collect_addons_launch_hook_paths())

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
        self.log.debug("Paths searched for launch hooks:\n{}".format(
            "\n".join("- {}".format(path) for path in paths)
        ))

        all_classes = discover_launch_hooks(paths, self.log)

        for launch_type, classes in all_classes.items():
            hooks_with_order = []
            hooks_without_order = []
            for klass in classes:
                try:
                    hook = klass(self)
                    if not hook.is_valid:
                        self.log.debug(
                            "Skipped hook invalid for current launch context: "
                            "{}".format(klass.__name__)
                        )
                        continue

                    if inspect.isabstract(hook):
                        self.log.debug("Skipped abstract hook: {}".format(
                            klass.__name__
                        ))
                        continue

                    # Separate hooks by pre/post class
                    if hook.order is None:
                        hooks_without_order.append(hook)
                    else:
                        hooks_with_order.append(hook)

                except Exception:
                    self.log.warning(
                        "Initialization of hook failed: "
                        "{}".format(klass.__name__),
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
        return self.application.name

    @property
    def host_name(self):
        return self.application.host_name

    @property
    def app_group(self):
        return self.application.group

    @property
    def manager(self):
        return self.application.manager

    def _run_process(self):
        # Windows and MacOS have easier process start
        low_platform = platform.system().lower()
        if low_platform in ("windows", "darwin"):
            return subprocess.Popen(self.launch_args, **self.kwargs)

        # Linux uses mid process
        # - it is possible that the mid process executable is not
        #   available for this version of OpenPype in that case use standard
        #   launch
        launch_args = get_linux_launcher_args()
        if launch_args is None:
            return subprocess.Popen(self.launch_args, **self.kwargs)

        # Prepare data that will be passed to midprocess
        # - store arguments to a json and pass path to json as last argument
        # - pass environments to set
        app_env = self.kwargs.pop("env", {})
        json_data = {
            "args": self.launch_args,
            "env": app_env
        }
        if app_env:
            # Filter environments of subprocess
            self.kwargs["env"] = {
                key: value
                for key, value in os.environ.items()
                if key in app_env
            }

        # Create temp file
        json_temp = tempfile.NamedTemporaryFile(
            mode="w", prefix="op_app_args", suffix=".json", delete=False
        )
        json_temp.close()
        json_temp_filpath = json_temp.name
        with open(json_temp_filpath, "w") as stream:
            json.dump(json_data, stream)

        launch_args.append(json_temp_filpath)

        # Create mid-process which will launch application
        process = subprocess.Popen(launch_args, **self.kwargs)
        # Wait until the process finishes
        #   - This is important! The process would stay in "open" state.
        process.wait()
        # Remove the temp file
        os.remove(json_temp_filpath)
        # Return process which is already terminated
        return process

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
        args_len_str = ""
        if isinstance(self.launch_args, str):
            args = self.launch_args
        else:
            args = self.clear_launch_args(self.launch_args)
            args_len_str = " ({})".format(len(args))
        self.log.info(
            "Launching \"{}\" with args{}: {}".format(
                self.application.full_name, args_len_str, args
            )
        )
        self.launch_args = args

        # Run process
        self.process = self._run_process()

        # Process post launch hooks
        for postlaunch_hook in self.postlaunch_hooks:
            self.log.debug("Executing postlaunch hook: {}".format(
                str(postlaunch_hook.__class__.__name__)
            ))

            # TODO how to handle errors?
            # - store to variable to let them accessible?
            try:
                postlaunch_hook.execute()

            except Exception:
                self.log.warning(
                    "After launch procedures were not successful.",
                    exc_info=True
                )

        self.log.debug("Launch of {} finished.".format(
            self.application.full_name
        ))

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
        if isinstance(args, str):
            return args
        all_cleared = False
        while not all_cleared:
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

        return args
