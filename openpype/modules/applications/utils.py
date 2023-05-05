import os
import platform
import subprocess
import json
import copy
import collections

import acre

from openpype.settings import (
    get_system_settings,
    get_project_settings,
    get_local_settings,
)
from openpype.client import get_project, get_asset_by_name
from openpype.modules import ModulesManager
from openpype.lib import filter_profiles, get_openpype_username
from openpype.lib.openpype_version import is_running_staging
from openpype.pipeline import AvalonMongoDB, Anatomy
from openpype.pipeline import HOST_WORKFILE_EXTENSIONS
from openpype.pipeline.template_data import get_template_data
from openpype.pipeline.workfile import (
    get_workdir_with_workdir_data,
    get_workfile_template_key,
    get_last_workfile
)
from .lib import (
    merge_env,
    EnvironmentPrepData,
    parse_environments,
)
from .exceptions import ApplicationLaunchFailed
from .manager import ApplicationManager


def should_workfile_tool_start(
    project_name, host_name, task_name, task_type, default_output=False
):
    """Define if host should start workfile tool at host launch.

    Default output is `False`. Can be overridden with environment variable
    `OPENPYPE_WORKFILE_TOOL_ON_START`, valid values without case sensitivity are
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
    profiles = (
        project_settings
        ["global"]
        ["tools"]
        ["Workfiles"]
        ["open_workfile_tool_on_startup"]
    )

    if not profiles:
        return default_output

    filter_data = {
        "tasks": task_name,
        "task_types": task_type,
        "hosts": host_name
    }
    matching_item = filter_profiles(profiles, filter_data)

    output = None
    if matching_item:
        output = matching_item.get("enabled")

    if output is None:
        return default_output
    return output


def should_start_last_workfile(
    project_name, host_name, task_name, task_type, default_output=False
):
    """Define if host should start last version workfile if possible.

    Default output is `False`. Can be overridden with environment variable
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
    profiles = (
        project_settings
        ["global"]
        ["tools"]
        ["Workfiles"]
        ["last_workfile_on_startup"]
    )

    if not profiles:
        return default_output

    filter_data = {
        "tasks": task_name,
        "task_types": task_type,
        "hosts": host_name
    }
    matching_item = filter_profiles(profiles, filter_data)

    output = None
    if matching_item:
        output = matching_item.get("enabled")

    if output is None:
        return default_output
    return output


def _prepare_last_workfile(data, workdir, modules_manager):
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


    if not modules_manager:
        modules_manager = ModulesManager()

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
    task_type = data["task_type"]

    start_last_workfile = data.get("start_last_workfile")
    if start_last_workfile is None:
        start_last_workfile = should_start_last_workfile(
            project_name, app.host_name, task_name, task_type
        )
    else:
        log.info("Opening of last workfile was disabled by user")

    data["start_last_workfile"] = start_last_workfile

    workfile_startup = should_workfile_tool_start(
        project_name, app.host_name, task_name, task_type
    )
    data["workfile_startup"] = workfile_startup

    # Store boolean as "0"(False) or "1"(True)
    data["env"]["AVALON_OPEN_LAST_WORKFILE"] = (
        str(int(bool(start_last_workfile)))
    )
    data["env"]["OPENPYPE_WORKFILE_TOOL_ON_START"] = (
        str(int(bool(workfile_startup)))
    )

    _sub_msg = "" if start_last_workfile else " not"
    log.debug(
        "Last workfile should{} be opened on start.".format(_sub_msg)
    )

    # Last workfile path
    last_workfile_path = data.get("last_workfile_path") or ""
    if not last_workfile_path:
        host_module = modules_manager.get_host_module(app.host_name)
        if host_module:
            extensions = host_module.get_workfile_extensions()
        else:
            extensions = HOST_WORKFILE_EXTENSIONS.get(app.host_name)

        if extensions:
            anatomy = data["anatomy"]
            project_settings = data["project_settings"]
            task_type = workdir_data["task"]["type"]
            template_key = get_workfile_template_key(
                task_type,
                app.host_name,
                project_name,
                project_settings=project_settings
            )
            # Find last workfile
            file_template = str(anatomy.templates[template_key]["file"])

            workdir_data.update({
                "version": 1,
                "user": get_openpype_username(),
                "ext": extensions[0]
            })

            last_workfile_path = get_last_workfile(
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


def apply_project_environments_value(
    project_name, env, project_settings=None, env_group=None
):
    """Apply project specific environments on passed environments.

    The environments are applied on passed `env` argument value so it is not
    required to apply changes back.

    Args:
        project_name (str): Name of project for which environments should be
            received.
        env (dict): Environment values on which project specific environments
            will be applied.
        project_settings (dict): Project settings for passed project name.
            Optional if project settings are already prepared.

    Returns:
        dict: Passed env values with applied project environments.

    Raises:
        KeyError: If project settings do not contain keys for project specific
            environments.
    """

    if project_settings is None:
        project_settings = get_project_settings(project_name)

    env_value = project_settings["global"]["project_environments"]
    if env_value:
        parsed_value = parse_environments(env_value, env_group)
        env.update(acre.compute(
            merge_env(parsed_value, env),
            cleanup=False
        ))
    return env


def get_app_environments_for_context(
    project_name,
    asset_name,
    task_name,
    app_name,
    env_group=None,
    env=None,
    modules_manager=None
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
        modules_manager (ModulesManager): Initialized modules manager.

    Returns:
        dict: Environments for passed context and application.
    """

    # Avalon database connection
    dbcon = AvalonMongoDB()
    dbcon.Session["AVALON_PROJECT"] = project_name
    dbcon.install()

    # Project document
    project_doc = get_project(project_name)
    asset_doc = get_asset_by_name(project_name, asset_name)

    if modules_manager is None:
        modules_manager = ModulesManager()

    # Prepare app object which can be obtained only from ApplciationManager
    app_manager = ApplicationManager()
    app = app_manager.applications[app_name]

    # Project's anatomy
    anatomy = Anatomy(project_name)

    data = EnvironmentPrepData({
        "project_name": project_name,
        "asset_name": asset_name,
        "task_name": task_name,

        "app": app,

        "dbcon": dbcon,
        "project_doc": project_doc,
        "asset_doc": asset_doc,

        "anatomy": anatomy,

        "env": env
    })
    data["env"].update(anatomy.root_environments())
    if is_running_staging():
        data["env"]["OPENPYPE_IS_STAGING"] = "1"

    prepare_app_environments(data, env_group, modules_manager)
    prepare_context_environments(data, env_group, modules_manager)

    # Discard avalon connection
    dbcon.uninstall()

    return data["env"]


def prepare_context_environments(data, env_group=None, modules_manager=None):
    """Modify launch environments with context data for launched host.

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
    project_settings = get_project_settings(project_name)
    system_settings = get_system_settings()
    data["project_settings"] = project_settings
    data["system_settings"] = system_settings
    # Apply project specific environments on current env value
    apply_project_environments_value(
        project_name, data["env"], project_settings, env_group
    )

    app = data["app"]
    context_env = {
        "AVALON_PROJECT": project_doc["name"],
        "AVALON_ASSET": asset_doc["name"],
        "AVALON_TASK": task_name,
        "AVALON_APP_NAME": app.full_name
    }

    log.debug(
        "Context environments set:\n{}".format(
            json.dumps(context_env, indent=4)
        )
    )
    data["env"].update(context_env)
    if not app.is_host:
        return

    workdir_data = get_template_data(
        project_doc, asset_doc, task_name, app.host_name, system_settings
    )
    data["workdir_data"] = workdir_data

    anatomy = data["anatomy"]

    task_type = workdir_data["task"]["type"]
    # Temp solution how to pass task type to `_prepare_last_workfile`
    data["task_type"] = task_type

    try:
        workdir = get_workdir_with_workdir_data(
            workdir_data,
            anatomy.project_name,
            anatomy,
            project_settings=project_settings
        )

    except Exception as exc:
        raise ApplicationLaunchFailed(
            "Error in anatomy.format: {}".format(str(exc))
        )

    if not os.path.exists(workdir):
        log.debug(
            "Creating workdir folder: \"{}\"".format(workdir)
        )
        try:
            os.makedirs(workdir)
        except Exception as exc:
            raise ApplicationLaunchFailed(
                "Couldn't create workdir because: {}".format(str(exc))
            )

    data["env"]["AVALON_APP"] = app.host_name
    data["env"]["AVALON_WORKDIR"] = workdir

    _prepare_last_workfile(data, workdir, modules_manager)


def _add_python_version_paths(app, env, logger, modules_manager):
    """Add vendor packages specific for a Python version."""

    for module in modules_manager.get_enabled_modules():
        module.modify_application_launch_arguments(app, env)

    # Skip adding if host name is not set
    if not app.host_name:
        return

    # Add Python 2/3 modules
    openpype_root = os.getenv("OPENPYPE_REPOS_ROOT")
    python_vendor_dir = os.path.join(
        openpype_root,
        "openpype",
        "vendor",
        "python"
    )
    if app.use_python_2:
        pythonpath = os.path.join(python_vendor_dir, "python_2")
    else:
        pythonpath = os.path.join(python_vendor_dir, "python_3")

    if not os.path.exists(pythonpath):
        return

    logger.debug("Adding Python version specific paths to PYTHONPATH")
    python_paths = [pythonpath]

    # Load PYTHONPATH from current launch context
    python_path = env.get("PYTHONPATH")
    if python_path:
        python_paths.append(python_path)

    # Set new PYTHONPATH to launch context environments
    env["PYTHONPATH"] = os.pathsep.join(python_paths)


def prepare_app_environments(
    data, env_group=None, implementation_envs=True, modules_manager=None
):
    """Modify launch environments based on launched app and context.

    Args:
        data (EnvironmentPrepData): Dictionary where result and intermediate
            result will be stored.
    """

    app = data["app"]
    log = data["log"]
    source_env = data["env"].copy()

    if modules_manager is None:
        modules_manager = ModulesManager()

    _add_python_version_paths(app, source_env, log, modules_manager)

    # Use environments from local settings
    filtered_local_envs = {}
    system_settings = data["system_settings"]
    whitelist_envs = system_settings["general"].get("local_env_white_list")
    if whitelist_envs:
        local_settings = get_local_settings()
        local_envs = local_settings.get("environments") or {}
        filtered_local_envs = {
            key: value
            for key, value in local_envs.items()
            if key in whitelist_envs
        }

    # Apply local environment variables for already existing values
    for key, value in filtered_local_envs.items():
        if key in source_env:
            source_env[key] = value

    # `app_and_tool_labels` has debug purpose
    app_and_tool_labels = [app.full_name]
    # Environments for application
    environments = [
        app.group.environment,
        app.environment
    ]

    asset_doc = data.get("asset_doc")
    # Add tools environments
    groups_by_name = {}
    tool_by_group_name = collections.defaultdict(dict)
    if asset_doc:
        # Make sure each tool group can be added only once
        for key in asset_doc["data"].get("tools_env") or []:
            tool = app.manager.tools.get(key)
            if not tool or not tool.is_valid_for_app(app):
                continue
            groups_by_name[tool.group.name] = tool.group
            tool_by_group_name[tool.group.name][tool.name] = tool

        for group_name in sorted(groups_by_name.keys()):
            group = groups_by_name[group_name]
            environments.append(group.environment)
            for tool_name in sorted(tool_by_group_name[group_name].keys()):
                tool = tool_by_group_name[group_name][tool_name]
                environments.append(tool.environment)
                app_and_tool_labels.append(tool.full_name)

    log.debug(
        "Will add environments for apps and tools: {}".format(
            ", ".join(app_and_tool_labels)
        )
    )

    env_values = {}
    for _env_values in environments:
        if not _env_values:
            continue

        # Choose right platform
        tool_env = parse_environments(_env_values, env_group)

        # Apply local environment variables
        # - must happen between all values because they may be used during
        #   merge
        for key, value in filtered_local_envs.items():
            if key in tool_env:
                tool_env[key] = value

        # Merge dictionaries
        env_values = merge_env(tool_env, env_values)

    merged_env = merge_env(env_values, source_env)

    loaded_env = acre.compute(merged_env, cleanup=False)

    final_env = None
    # Add host specific environments
    if app.host_name and implementation_envs:
        host_module = modules_manager.get_host_module(app.host_name)
        if not host_module:
            module = __import__("openpype.hosts", fromlist=[app.host_name])
            host_module = getattr(module, app.host_name, None)
        add_implementation_envs = None
        if host_module:
            add_implementation_envs = getattr(
                host_module, "add_implementation_envs", None
            )
        if add_implementation_envs:
            # Function may only modify passed dict without returning value
            final_env = add_implementation_envs(loaded_env, app)

    if final_env is None:
        final_env = loaded_env

    keys_to_remove = set(source_env.keys()) - set(final_env.keys())

    # Update env
    data["env"].update(final_env)
    for key in keys_to_remove:
        data["env"].pop(key, None)


def get_non_python_host_kwargs(kwargs, allow_console=True):
    """Explicit setting of kwargs for Popen for AE/PS/Harmony.

    Expected behavior
    - openpype_console opens window with logs
    - openpype_gui has stdout/stderr available for capturing

    Args:
        kwargs (dict) or None
        allow_console (bool): use False for inner Popen opening app itself or
           it will open additional console (at least for Harmony)
    """
    if kwargs is None:
        kwargs = {}

    if platform.system().lower() != "windows":
        return kwargs

    executable_path = os.environ.get("OPENPYPE_EXECUTABLE")
    executable_filename = ""
    if executable_path:
        executable_filename = os.path.basename(executable_path)
    if "openpype_gui" in executable_filename:
        kwargs.update({
            "creationflags": subprocess.CREATE_NO_WINDOW,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL
        })
    elif allow_console:
        kwargs.update({
            "creationflags": subprocess.CREATE_NEW_CONSOLE
        })
    return kwargs
