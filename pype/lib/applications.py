import os
import sys
import re
import getpass
import json
import copy
import platform
import inspect
import logging
import subprocess
from abc import ABCMeta, abstractmethod

import six
import acre

import avalon.lib
import avalon.api

from ..api import (
    Anatomy,
    Logger,
    config,
    system_settings,
    environments
)
from .python_module_tools import (
    modules_from_path,
    classes_from_module
)
from .hooks import execute_hook
from .deprecated import get_avalon_database
from .env_tools import env_value_to_bool

log = logging.getLogger(__name__)


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
            for executable_path in application.executables:
                details += "\n- " + executable_path

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


def compile_list_of_regexes(in_list):
    """Convert strings in entered list to compiled regex objects."""
    regexes = list()
    if not in_list:
        return regexes

    for item in in_list:
        if item:
            try:
                regexes.append(re.compile(item))
            except TypeError:
                print((
                    "Invalid type \"{}\" value \"{}\"."
                    " Expected string based object. Skipping."
                ).format(str(type(item)), str(item)))
    return regexes


def launch_application(project_name, asset_name, task_name, app_name):
    """Launch host application with filling required environments.

    TODO(iLLiCiT): This should be split into more parts.
    """
    # `get_avalon_database` is in Pype 3 replaced with using `AvalonMongoDB`
    database = get_avalon_database()
    project_document = database[project_name].find_one({"type": "project"})
    asset_document = database[project_name].find_one({
        "type": "asset",
        "name": asset_name
    })

    asset_doc_parents = asset_document["data"].get("parents")
    hierarchy = "/".join(asset_doc_parents)

    app_def = avalon.lib.get_application(app_name)
    app_label = app_def.get("ftrack_label", app_def.get("label", app_name))

    host_name = app_def["application_dir"]
    # Workfile data collection may be special function?
    data = {
        "project": {
            "name": project_document["name"],
            "code": project_document["data"].get("code")
        },
        "task": task_name,
        "asset": asset_name,
        "app": host_name,
        "hierarchy": hierarchy
    }

    try:
        anatomy = Anatomy(project_name)
        anatomy_filled = anatomy.format(data)
        workdir = os.path.normpath(anatomy_filled["work"]["folder"])

    except Exception as exc:
        raise ApplicationLaunchFailed(
            "Error in anatomy.format: {}".format(str(exc))
        )

    try:
        os.makedirs(workdir)
    except FileExistsError:
        pass

    last_workfile_path = None
    extensions = avalon.api.HOST_WORKFILE_EXTENSIONS.get(host_name)
    if extensions:
        # Find last workfile
        file_template = anatomy.templates["work"]["file"]
        data.update({
            "version": 1,
            "user": os.environ.get("PYPE_USERNAME") or getpass.getuser(),
            "ext": extensions[0]
        })

        last_workfile_path = avalon.api.last_workfile(
            workdir, file_template, data, extensions, True
        )

    # set environments for Avalon
    prep_env = copy.deepcopy(os.environ)
    prep_env.update({
        "AVALON_PROJECT": project_name,
        "AVALON_ASSET": asset_name,
        "AVALON_TASK": task_name,
        "AVALON_APP": host_name,
        "AVALON_APP_NAME": app_name,
        "AVALON_HIERARCHY": hierarchy,
        "AVALON_WORKDIR": workdir
    })

    start_last_workfile = avalon.api.should_start_last_workfile(
        project_name, host_name, task_name
    )
    # Store boolean as "0"(False) or "1"(True)
    prep_env["AVALON_OPEN_LAST_WORKFILE"] = (
        str(int(bool(start_last_workfile)))
    )

    if (
        start_last_workfile
        and last_workfile_path
        and os.path.exists(last_workfile_path)
    ):
        prep_env["AVALON_LAST_WORKFILE"] = last_workfile_path

    prep_env.update(anatomy.roots_obj.root_environments())

    # collect all the 'environment' attributes from parents
    tools_attr = [prep_env["AVALON_APP"], prep_env["AVALON_APP_NAME"]]
    tools_env = asset_document["data"].get("tools_env") or []
    tools_attr.extend(tools_env)

    tools_env = acre.get_tools(tools_attr)
    env = acre.compute(tools_env)
    env = acre.merge(env, current_env=dict(prep_env))

    # Get path to execute
    st_temp_path = os.environ["PYPE_CONFIG"]
    os_plat = platform.system().lower()

    # Path to folder with launchers
    path = os.path.join(st_temp_path, "launchers", os_plat)

    # Full path to executable launcher
    execfile = None

    launch_hook = app_def.get("launch_hook")
    if launch_hook:
        log.info("launching hook: {}".format(launch_hook))
        ret_val = execute_hook(launch_hook, env=env)
        if not ret_val:
            raise ApplicationLaunchFailed(
                "Hook didn't finish successfully {}".format(app_label)
            )

    if sys.platform == "win32":
        for ext in os.environ["PATHEXT"].split(os.pathsep):
            fpath = os.path.join(path.strip('"'), app_def["executable"] + ext)
            if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                execfile = fpath
                break

        # Run SW if was found executable
        if execfile is None:
            raise ApplicationLaunchFailed(
                "We didn't find launcher for {}".format(app_label)
            )

        popen = avalon.lib.launch(
            executable=execfile, args=[], environment=env
        )

    elif (
        sys.platform.startswith("linux")
        or sys.platform.startswith("darwin")
    ):
        execfile = os.path.join(path.strip('"'), app_def["executable"])
        # Run SW if was found executable
        if execfile is None:
            raise ApplicationLaunchFailed(
                "We didn't find launcher for {}".format(app_label)
            )

        if not os.path.isfile(execfile):
            raise ApplicationLaunchFailed(
                "Launcher doesn't exist - {}".format(execfile)
            )

        try:
            fp = open(execfile)
        except PermissionError as perm_exc:
            raise ApplicationLaunchFailed(
                "Access denied on launcher {} - {}".format(execfile, perm_exc)
            )

        fp.close()
        # check executable permission
        if not os.access(execfile, os.X_OK):
            raise ApplicationLaunchFailed(
                "No executable permission - {}".format(execfile)
            )

        popen = avalon.lib.launch(  # noqa: F841
            "/usr/bin/env", args=["bash", execfile], environment=env
        )
    return popen


class ApplicationAction:
    """Default application launcher

    This is a convenience application Action that when "config" refers to a
    parsed application `.toml` this can launch the application.

    """
    _log = None
    config = None
    group = None
    variant = None
    required_session_keys = (
        "AVALON_PROJECT",
        "AVALON_ASSET",
        "AVALON_TASK"
    )

    @property
    def log(self):
        if self._log is None:
            self._log = Logger().get_logger(self.__class__.__name__)
        return self._log

    def is_compatible(self, session):
        for key in self.required_session_keys:
            if key not in session:
                return False
        return True

    def process(self, session, **kwargs):
        """Process the full Application action"""

        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]
        task_name = session["AVALON_TASK"]
        launch_application(
            project_name, asset_name, task_name, self.name
        )

        self._ftrack_after_launch_procedure(
            project_name, asset_name, task_name
        )

    def _ftrack_after_launch_procedure(
        self, project_name, asset_name, task_name
    ):
        # TODO move to launch hook
        required_keys = ("FTRACK_SERVER", "FTRACK_API_USER", "FTRACK_API_KEY")
        for key in required_keys:
            if not os.environ.get(key):
                self.log.debug((
                    "Missing required environment \"{}\""
                    " for Ftrack after launch procedure."
                ).format(key))
                return

        try:
            import ftrack_api
            session = ftrack_api.Session(auto_connect_event_hub=True)
            self.log.debug("Ftrack session created")
        except Exception:
            self.log.warning("Couldn't create Ftrack session")
            return

        try:
            entity = self._find_ftrack_task_entity(
                session, project_name, asset_name, task_name
            )
            self._ftrack_status_change(session, entity, project_name)
            self._start_timer(session, entity, ftrack_api)
        except Exception:
            self.log.warning(
                "Couldn't finish Ftrack procedure.", exc_info=True
            )
            return

        finally:
            session.close()

    def _find_ftrack_task_entity(
        self, session, project_name, asset_name, task_name
    ):
        project_entity = session.query(
            "Project where full_name is \"{}\"".format(project_name)
        ).first()
        if not project_entity:
            self.log.warning(
                "Couldn't find project \"{}\" in Ftrack.".format(project_name)
            )
            return

        potential_task_entities = session.query((
            "TypedContext where parent.name is \"{}\" and project_id is \"{}\""
        ).format(asset_name, project_entity["id"])).all()
        filtered_entities = []
        for _entity in potential_task_entities:
            if (
                _entity.entity_type.lower() == "task"
                and _entity["name"] == task_name
            ):
                filtered_entities.append(_entity)

        if not filtered_entities:
            self.log.warning((
                "Couldn't find task \"{}\" under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        if len(filtered_entities) > 1:
            self.log.warning((
                "Found more than one task \"{}\""
                " under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        return filtered_entities[0]

    def _ftrack_status_change(self, session, entity, project_name):
        presets = config.get_presets(project_name)["ftrack"]["ftrack_config"]
        statuses = presets.get("status_update")
        if not statuses:
            return

        actual_status = entity["status"]["name"].lower()
        already_tested = set()
        ent_path = "/".join(
            [ent["name"] for ent in entity["link"]]
        )
        while True:
            next_status_name = None
            for key, value in statuses.items():
                if key in already_tested:
                    continue
                if actual_status in value or "_any_" in value:
                    if key != "_ignore_":
                        next_status_name = key
                        already_tested.add(key)
                    break
                already_tested.add(key)

            if next_status_name is None:
                break

            try:
                query = "Status where name is \"{}\"".format(
                    next_status_name
                )
                status = session.query(query).one()

                entity["status"] = status
                session.commit()
                self.log.debug("Changing status to \"{}\" <{}>".format(
                    next_status_name, ent_path
                ))
                break

            except Exception:
                session.rollback()
                msg = (
                    "Status \"{}\" in presets wasn't found"
                    " on Ftrack entity type \"{}\""
                ).format(next_status_name, entity.entity_type)
                self.log.warning(msg)

    def _start_timer(self, session, entity, _ftrack_api):
        self.log.debug("Triggering timer start.")

        user_entity = session.query("User where username is \"{}\"".format(
            os.environ["FTRACK_API_USER"]
        )).first()
        if not user_entity:
            self.log.warning(
                "Couldn't find user with username \"{}\" in Ftrack".format(
                    os.environ["FTRACK_API_USER"]
                )
            )
            return

        source = {
            "user": {
                "id": user_entity["id"],
                "username": user_entity["username"]
            }
        }
        event_data = {
            "actionIdentifier": "start.timer",
            "selection": [{"entityId": entity["id"], "entityType": "task"}]
        }
        session.event_hub.publish(
            _ftrack_api.event.base.Event(
                topic="ftrack.action.launch",
                data=event_data,
                source=source
            ),
            on_error="ignore"
        )
        self.log.debug("Timer start triggered successfully.")


# Special naming case for subprocess since its a built-in method.
def _subprocess(*args, **kwargs):
    """Convenience method for getting output errors for subprocess.

    Entered arguments and keyword arguments are passed to subprocess Popen.

    Args:
        *args: Variable length arument list passed to Popen.
        **kwargs : Arbitary keyword arguments passed to Popen. Is possible to
            pass `logging.Logger` object under "logger" if want to use
            different than lib's logger.

    Returns:
        str: Full output of subprocess concatenated stdout and stderr.

    Raises:
        RuntimeError: Exception is raised if process finished with nonzero
            return code.
    """

    # Get environents from kwarg or use current process environments if were
    # not passed.
    env = kwargs.get("env") or os.environ
    # Make sure environment contains only strings
    filtered_env = {k: str(v) for k, v in env.items()}

    # Use lib's logger if was not passed with kwargs.
    logger = kwargs.pop("logger", log)

    # set overrides
    kwargs['stdout'] = kwargs.get('stdout', subprocess.PIPE)
    kwargs['stderr'] = kwargs.get('stderr', subprocess.PIPE)
    kwargs['stdin'] = kwargs.get('stdin', subprocess.PIPE)
    kwargs['env'] = filtered_env

    proc = subprocess.Popen(*args, **kwargs)

    full_output = ""
    _stdout, _stderr = proc.communicate()
    if _stdout:
        _stdout = _stdout.decode("utf-8")
        full_output += _stdout
        logger.debug(_stdout)

    if _stderr:
        _stderr = _stderr.decode("utf-8")
        # Add additional line break if output already containt stdout
        if full_output:
            full_output += "\n"
        full_output += _stderr
        logger.warning(_stderr)

    if proc.returncode != 0:
        exc_msg = "Executing arguments was not successful: \"{}\"".format(args)
        if _stdout:
            exc_msg += "\n\nOutput:\n{}".format(_stdout)

        if _stderr:
            exc_msg += "Error:\n{}".format(_stderr)

        raise RuntimeError(exc_msg)

    return full_output


class ApplicationManager:
    def __init__(self):
        self.log = Logger().get_logger(self.__class__.__name__)

        self.applications = {}
        self.tools = {}

        self.refresh()

    def refresh(self):
        """Refresh applications from settings."""
        settings = system_settings()

        hosts_definitions = settings["global"]["applications"]
        for host_name, variant_definitions in hosts_definitions.items():
            enabled = variant_definitions["enabled"]
            label = variant_definitions.get("label") or host_name
            variants = variant_definitions.get("variants") or {}
            icon = variant_definitions.get("icon")
            is_host = variant_definitions.get("is_host", False)
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

                is_host = app_data.get("is_host", is_host)
                app_data["is_host"] = is_host

                self.applications[app_name] = Application(
                    host_name, app_name, app_data, self
                )

        tools_definitions = settings["global"]["tools"]
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


class Application:
    """Hold information about application.

    Object by itself does nothing special.

    Args:
        host_name (str): Host name or rather name of host implementation.
            e.g. "maya", "nuke", "photoshop", etc.
        app_name (str): Specific version (or variant) of host.
            e.g. "maya2020", "nuke11.3", etc.
        app_data (dict): Data for the version containing information about
            executables, label, variant label, icon or if is enabled.
            Only required key is `executables`.
        manager (ApplicationManager): Application manager that created object.
    """

    def __init__(self, host_name, app_name, app_data, manager):
        self.host_name = host_name
        self.app_name = app_name
        self.app_data = app_data
        self.manager = manager

        self.label = app_data.get("label") or app_name
        self.variant_label = app_data.get("variant_label") or None
        self.icon = app_data.get("icon") or None
        self.enabled = app_data.get("enabled", True)
        self.is_host = app_data.get("is_host", False)

        executables = app_data["executables"]
        if isinstance(executables, dict):
            executables = executables.get(platform.system().lower()) or []

        if not isinstance(executables, list):
            executables = [executables]
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
        for executable_path in self.executables:
            if os.path.exists(executable_path):
                return executable_path
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
    """Abstract class from all hooks should inherit."""
    # Order of prelaunch hook, will be executed as last if set to None.
    order = None
    # If hook should be executed befor or after application launch
    prelaunch = True
    # List of host implementations, skipped if empty.
    hosts = []
    # List of platform availability, skipped if empty.
    platforms = []

    def __init__(self, launch_context):
        """Constructor of launch hook.

        Always should be called
        """
        self.log = logging.getLogger(self.__class__.__name__)

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

        return True

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
        executable (str): Path to executable.
        **data (dict): Any additional data. Data may be used during
            preparation to store objects usable in multiple places.
    """
    def __init__(self, application, executable, **data):
        # Application object
        self.application = application

        # Logger
        logger_name = "{}-{}".format(self.__class__.__name__, self.app_name)
        self.log = Logger().get_logger(logger_name)

        self.executable = executable

        self.data = dict(data)

        # Handle launch environemtns
        passed_env = self.data.pop("env", None)
        if passed_env is None:
            env = os.environ
        else:
            env = passed_env
        self.env = copy.deepcopy(env)

        # Load settings if were not passed in data
        settings_env = self.data.get("settings_env")
        if settings_env is None:
            settings_env = environments()
            self.data["settings_env"] = settings_env

        # subprocess.Popen launch arguments (first argument in constructor)
        self.launch_args = [executable]
        # subprocess.Popen keyword arguments
        self.kwargs = {
            "env": self.env
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

        # TODO move these to pre-paunch hook
        self.prepare_global_data()
        self.prepare_host_environments()
        self.prepare_context_environments()

    def paths_to_launch_hooks(self):
        """Directory paths where to look for launch hooks."""
        # This method has potential to be part of application manager (maybe).

        # TODO find better way how to define dir path to default launch hooks
        import pype
        pype_dir = os.path.dirname(os.path.abspath(pype.__file__))
        hooks_dir = os.path.join(pype_dir, "hooks")

        # TODO load additional studio paths from settings
        # TODO add paths based on used modules (like `ftrack`)
        paths = []
        subfolder_names = ["global", self.host_name, self.app_name]
        for subfolder_name in subfolder_names:
            path = os.path.join(hooks_dir, subfolder_name)
            if os.path.exists(path) and os.path.isdir(path):
                paths.append(path)
        return paths

    def discover_launch_hooks(self, force=False):
        if (
            self.prelaunch_hooks is not None
            or self.postlaunch_hooks is not None
        ):
            if not force:
                self.log.info("Launch hooks were already discovered.")
                return

            self.prelaunch_hooks.clear()
            self.postlaunch_hooks.clear()

        classes = []
        paths = self.paths_to_launch_hooks()
        for path in paths:
            if not os.path.exists(path):
                self.log.info(
                    "Path to launch hooks does not exists: \"{}\"".format(path)
                )
                continue

            modules = modules_from_path(path)
            for _module in modules:
                classes.extend(classes_from_module(LaunchHook, _module))

        pre_hooks_with_order = []
        pre_hooks_without_order = []
        post_hooks_with_order = []
        post_hooks_without_order = []
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

                # Separate hooks if should be executed before or after launch
                if hook.prelaunch:
                    if hook.order is None:
                        pre_hooks_without_order.append(hook)
                    else:
                        pre_hooks_with_order.append(hook)
                else:
                    if hook.order is None:
                        post_hooks_with_order.append(hook)
                    else:
                        post_hooks_without_order.append(hook)

            except Exception:
                self.log.warning(
                    "Initialization of hook failed. {}".format(str(klass)),
                    exc_info=True
                )

        # Sort hooks with order by order
        pre_hooks_ordered = list(sorted(
            pre_hooks_with_order, key=lambda obj: obj.order
        ))
        post_hooks_ordered = list(sorted(
            post_hooks_with_order, key=lambda obj: obj.order
        ))

        # Extend ordered hooks with hooks without defined order
        pre_hooks_ordered.extend(pre_hooks_without_order)
        post_hooks_ordered.extend(post_hooks_without_order)

        self.prelaunch_hooks = pre_hooks_ordered
        self.postlaunch_hooks = post_hooks_ordered

    @property
    def app_name(self):
        return self.application.app_name

    @property
    def host_name(self):
        return self.application.host_name

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
            prelaunch_hook.execute()

        # Prepare subprocess args
        args = self.clear_launch_args(self.launch_args)
        self.log.debug(
            "Launching \"{}\" with args: {}".format(self.app_name, args)
        )
        # Run process
        self.process = subprocess.Popen(args, **self.kwargs)

        # Process post launch hooks
        for postlaunch_hook in self.postlaunch_hooks:
            try:
                postlaunch_hook.execute()

            except Exception:
                self.log.warning(
                    "After launch procedures were not successful.",
                    exc_info=True
                )

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
                    new_args.append(args)
            args = new_args

            if all_cleared:
                break
        return args

    def prepare_global_data(self):
        """Prepare global objects to `data` that will be used for sure."""
        # Mongo documents
        project_name = self.data.get("project_name")
        if not project_name:
            self.log.info(
                "Skipping global data preparation."
                " Key `project_name` was not found in launch context."
            )
            return

        self.log.debug("Project name is set to \"{}\"".format(project_name))
        # Anatomy
        self.data["anatomy"] = Anatomy(project_name)

        # Mongo connection
        dbcon = avalon.api.AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name
        dbcon.install()

        self.data["dbcon"] = dbcon

        # Project document
        project_doc = dbcon.find_one({"type": "project"})
        self.data["project_doc"] = project_doc

        asset_name = self.data.get("asset_name")
        if not asset_name:
            self.log.warning(
                "Asset name was not set. Skipping asset document query."
            )
            return

        asset_doc = dbcon.find_one({
            "type": "asset",
            "name": asset_name
        })
        self.data["asset_doc"] = asset_doc

    def _merge_env(self, env, current_env):
        """Modified function(merge) from acre module."""
        result = current_env.copy()
        for key, value in env.items():
            # Keep missing keys by not filling `missing` kwarg
            value = acre.lib.partial_format(value, data=current_env)
            result[key] = value
        return result

    def prepare_host_environments(self):
        """Modify launch environments based on launched app and context."""
        # Keys for getting environments
        env_keys = [self.host_name, self.app_name]

        asset_doc = self.data.get("asset_doc")
        if asset_doc:
            # Add tools environments
            for key in asset_doc["data"].get("tools_env") or []:
                tool = self.manager.tools.get(key)
                if tool:
                    if tool.group_name not in env_keys:
                        env_keys.append(tool.group_name)

                    if tool.name not in env_keys:
                        env_keys.append(tool.name)

        self.log.debug(
            "Finding environment groups for keys: {}".format(env_keys)
        )

        settings_env = self.data["settings_env"]
        env_values = {}
        for env_key in env_keys:
            _env_values = settings_env.get(env_key)
            if not _env_values:
                continue

            # Choose right platform
            tool_env = acre.parse(_env_values)
            # Merge dictionaries
            env_values = self._merge_env(tool_env, env_values)

        final_env = self._merge_env(acre.compute(env_values), self.env)

        # Update env
        self.env.update(final_env)

    def prepare_context_environments(self):
        """Modify launch environemnts with context data for launched host."""
        # Context environments
        project_doc = self.data.get("project_doc")
        asset_doc = self.data.get("asset_doc")
        task_name = self.data.get("task_name")
        if (
            not project_doc
            or not asset_doc
            or not task_name
        ):
            self.log.info(
                "Skipping context environments preparation."
                " Launch context does not contain required data."
            )
            return

        workdir_data = self._prepare_workdir_data(
            project_doc, asset_doc, task_name
        )
        self.data["workdir_data"] = workdir_data

        hierarchy = workdir_data["hierarchy"]
        anatomy = self.data["anatomy"]

        try:
            anatomy_filled = anatomy.format(workdir_data)
            workdir = os.path.normpath(anatomy_filled["work"]["folder"])
            if not os.path.exists(workdir):
                self.log.debug(
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
            "AVALON_APP": self.host_name,
            "AVALON_APP_NAME": self.app_name,
            "AVALON_HIERARCHY": hierarchy,
            "AVALON_WORKDIR": workdir
        }
        self.log.debug(
            "Context environemnts set:\n{}".format(
                json.dumps(context_env, indent=4)
            )
        )
        self.env.update(context_env)

        self.prepare_last_workfile(workdir)

    def _prepare_workdir_data(self, project_doc, asset_doc, task_name):
        hierarchy = "/".join(asset_doc["data"]["parents"])

        data = {
            "project": {
                "name": project_doc["name"],
                "code": project_doc["data"].get("code")
            },
            "task": task_name,
            "asset": asset_doc["name"],
            "app": self.host_name,
            "hierarchy": hierarchy
        }
        return data

    def prepare_last_workfile(self, workdir):
        """last workfile workflow preparation.

        Function check if should care about last workfile workflow and tries
        to find the last workfile. Both information are stored to `data` and
        environments.

        Last workfile is filled always (with version 1) even if any workfile
        exists yet.

        Args:
            workdir (str): Path to folder where workfiles should be stored.
        """
        _workdir_data = self.data.get("workdir_data")
        if not _workdir_data:
            self.log.info(
                "Skipping last workfile preparation."
                " Key `workdir_data` not filled."
            )
            return

        workdir_data = copy.deepcopy(_workdir_data)
        project_name = self.data["project_name"]
        task_name = self.data["task_name"]
        start_last_workfile = self.should_start_last_workfile(
            project_name, self.host_name, task_name
        )
        self.data["start_last_workfile"] = start_last_workfile

        # Store boolean as "0"(False) or "1"(True)
        self.env["AVALON_OPEN_LAST_WORKFILE"] = (
            str(int(bool(start_last_workfile)))
        )

        _sub_msg = "" if start_last_workfile else " not"
        self.log.debug(
            "Last workfile should{} be opened on start.".format(_sub_msg)
        )

        # Last workfile path
        last_workfile_path = ""
        extensions = avalon.api.HOST_WORKFILE_EXTENSIONS.get(self.host_name)
        if extensions:
            anatomy = self.data["anatomy"]
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
            self.log.debug((
                "Workfiles for launch context does not exists"
                " yet but path will be set."
            ))
        self.log.debug(
            "Setting last workfile path: {}".format(last_workfile_path)
        )

        self.env["AVALON_LAST_WORKFILE"] = last_workfile_path
        self.data["last_workfile_path"] = last_workfile_path

    def should_start_last_workfile(self, project_name, host_name, task_name):
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
        default_output = env_value_to_bool(
            "AVALON_OPEN_LAST_WORKFILE", default=False
        )
        # TODO convert to settings
        try:
            startup_presets = (
                config.get_presets(project_name)
                .get("tools", {})
                .get("workfiles", {})
                .get("last_workfile_on_startup")
            )
        except Exception:
            startup_presets = None
            self.log.warning("Couldn't load pype's presets", exc_info=True)

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

    def after_launch_procedures(self):
        self._ftrack_after_launch_procedure()

    def _ftrack_after_launch_procedure(self):
        # TODO move to launch hook
        project_name = self.data.get("project_name")
        asset_name = self.data.get("asset_name")
        task_name = self.data.get("task_name")
        if (
            not project_name
            or not asset_name
            or not task_name
        ):
            return

        required_keys = ("FTRACK_SERVER", "FTRACK_API_USER", "FTRACK_API_KEY")
        for key in required_keys:
            if not os.environ.get(key):
                self.log.debug((
                    "Missing required environment \"{}\""
                    " for Ftrack after launch procedure."
                ).format(key))
                return

        try:
            import ftrack_api
            session = ftrack_api.Session(auto_connect_event_hub=True)
            self.log.debug("Ftrack session created")
        except Exception:
            self.log.warning("Couldn't create Ftrack session")
            return

        try:
            entity = self._find_ftrack_task_entity(
                session, project_name, asset_name, task_name
            )
            self._ftrack_status_change(session, entity, project_name)
            self._start_timer(session, entity, ftrack_api)
        except Exception:
            self.log.warning(
                "Couldn't finish Ftrack procedure.", exc_info=True
            )
            return

        finally:
            session.close()

    def _find_ftrack_task_entity(
        self, session, project_name, asset_name, task_name
    ):
        project_entity = session.query(
            "Project where full_name is \"{}\"".format(project_name)
        ).first()
        if not project_entity:
            self.log.warning(
                "Couldn't find project \"{}\" in Ftrack.".format(project_name)
            )
            return

        potential_task_entities = session.query((
            "TypedContext where parent.name is \"{}\" and project_id is \"{}\""
        ).format(asset_name, project_entity["id"])).all()
        filtered_entities = []
        for _entity in potential_task_entities:
            if (
                _entity.entity_type.lower() == "task"
                and _entity["name"] == task_name
            ):
                filtered_entities.append(_entity)

        if not filtered_entities:
            self.log.warning((
                "Couldn't find task \"{}\" under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        if len(filtered_entities) > 1:
            self.log.warning((
                "Found more than one task \"{}\""
                " under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        return filtered_entities[0]

    def _ftrack_status_change(self, session, entity, project_name):
        from pype.api import config
        presets = config.get_presets(project_name)["ftrack"]["ftrack_config"]
        statuses = presets.get("status_update")
        if not statuses:
            return

        actual_status = entity["status"]["name"].lower()
        already_tested = set()
        ent_path = "/".join(
            [ent["name"] for ent in entity["link"]]
        )
        while True:
            next_status_name = None
            for key, value in statuses.items():
                if key in already_tested:
                    continue
                if actual_status in value or "_any_" in value:
                    if key != "_ignore_":
                        next_status_name = key
                        already_tested.add(key)
                    break
                already_tested.add(key)

            if next_status_name is None:
                break

            try:
                query = "Status where name is \"{}\"".format(
                    next_status_name
                )
                status = session.query(query).one()

                entity["status"] = status
                session.commit()
                self.log.debug("Changing status to \"{}\" <{}>".format(
                    next_status_name, ent_path
                ))
                break

            except Exception:
                session.rollback()
                msg = (
                    "Status \"{}\" in presets wasn't found"
                    " on Ftrack entity type \"{}\""
                ).format(next_status_name, entity.entity_type)
                self.log.warning(msg)

    def _start_timer(self, session, entity, _ftrack_api):
        self.log.debug("Triggering timer start.")

        user_entity = session.query("User where username is \"{}\"".format(
            os.environ["FTRACK_API_USER"]
        )).first()
        if not user_entity:
            self.log.warning(
                "Couldn't find user with username \"{}\" in Ftrack".format(
                    os.environ["FTRACK_API_USER"]
                )
            )
            return

        source = {
            "user": {
                "id": user_entity["id"],
                "username": user_entity["username"]
            }
        }
        event_data = {
            "actionIdentifier": "start.timer",
            "selection": [{"entityId": entity["id"], "entityType": "task"}]
        }
        session.event_hub.publish(
            _ftrack_api.event.base.Event(
                topic="ftrack.action.launch",
                data=event_data,
                source=source
            ),
            on_error="ignore"
        )
        self.log.debug("Timer start triggered successfully.")
