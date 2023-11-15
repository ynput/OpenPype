"""Core pipeline functionality"""

import os
import json
import types
import logging
import platform
import uuid

import pyblish.api
from pyblish.lib import MessageHandler

import openpype
from openpype import AYON_SERVER_ENABLED
from openpype.host import HostBase
from openpype.client import (
    get_project,
    get_asset_by_id,
    get_asset_by_name,
    version_is_latest,
    get_asset_name_identifier,
    get_ayon_server_api_connection,
)
from openpype.lib.events import emit_event
from openpype.modules import load_modules, ModulesManager
from openpype.settings import get_project_settings
from openpype.tests.lib import is_in_tests

from .publish.lib import filter_pyblish_plugins
from .anatomy import Anatomy
from .template_data import get_template_data_with_names
from .workfile import (
    get_workfile_template_key,
    get_custom_workfile_template_by_string_context,
)
from . import (
    legacy_io,
    register_loader_plugin_path,
    register_inventory_action_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_inventory_action_path
)


_is_installed = False
_process_id = None
_registered_root = {"_": {}}
_registered_host = {"_": None}
# Keep modules manager (and it's modules) in memory
# - that gives option to register modules' callbacks
_modules_manager = None

log = logging.getLogger(__name__)

PACKAGE_DIR = os.path.dirname(os.path.abspath(openpype.__file__))
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def _get_modules_manager():
    """Get or create modules manager for host installation.

    This is not meant for public usage. Reason is to keep modules
    in memory of process to be able trigger their event callbacks if they
    need any.

    Returns:
        ModulesManager: Manager wrapping discovered modules.
    """

    global _modules_manager
    if _modules_manager is None:
        _modules_manager = ModulesManager()
    return _modules_manager


def register_root(path):
    """Register currently active root"""
    log.info("Registering root: %s" % path)
    _registered_root["_"] = path


def registered_root():
    """Return registered roots from current project anatomy.

    Consider this does return roots only for current project and current
        platforms, only if host was installer using 'install_host'.

    Deprecated:
        Please use project 'Anatomy' to get roots. This function is still used
            at current core functions of load logic, but that will change
            in future and this function will be removed eventually. Using this
            function at new places can cause problems in the future.

    Returns:
        dict[str, str]: Root paths.
    """

    return _registered_root["_"]


def install_host(host):
    """Install `host` into the running Python session.

    Args:
        host (module): A Python module containing the Avalon
            avalon host-interface.
    """
    global _is_installed

    _is_installed = True

    # Make sure global AYON connection has set site id and version
    if AYON_SERVER_ENABLED:
        get_ayon_server_api_connection()

    legacy_io.install()
    modules_manager = _get_modules_manager()

    missing = list()
    for key in ("AVALON_PROJECT", "AVALON_ASSET"):
        if key not in legacy_io.Session:
            missing.append(key)

    assert not missing, (
        "%s missing from environment, %s" % (
            ", ".join(missing),
            json.dumps(legacy_io.Session, indent=4, sort_keys=True)
        ))

    project_name = legacy_io.Session["AVALON_PROJECT"]
    log.info("Activating %s.." % project_name)

    # Optional host install function
    if hasattr(host, "install"):
        host.install()

    register_host(host)

    def modified_emit(obj, record):
        """Method replacing `emit` in Pyblish's MessageHandler."""
        record.msg = record.getMessage()
        obj.records.append(record)

    MessageHandler.emit = modified_emit

    if os.environ.get("OPENPYPE_REMOTE_PUBLISH"):
        # target "farm" == rendering on farm, expects OPENPYPE_PUBLISH_DATA
        # target "remote" == remote execution, installs host
        print("Registering pyblish target: remote")
        pyblish.api.register_target("remote")
    else:
        pyblish.api.register_target("local")

    if is_in_tests():
        print("Registering pyblish target: automated")
        pyblish.api.register_target("automated")

    project_name = os.environ.get("AVALON_PROJECT")
    host_name = os.environ.get("AVALON_APP")

    # Give option to handle host installation
    for module in modules_manager.get_enabled_modules():
        module.on_host_install(host, host_name, project_name)

    install_openpype_plugins(project_name, host_name)


def install_openpype_plugins(project_name=None, host_name=None):
    # Make sure modules are loaded
    load_modules()

    log.info("Registering global plug-ins..")
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    pyblish.api.register_discovery_filter(filter_pyblish_plugins)
    register_loader_plugin_path(LOAD_PATH)
    register_inventory_action_path(INVENTORY_PATH)

    if host_name is None:
        host_name = os.environ.get("AVALON_APP")

    modules_manager = _get_modules_manager()
    publish_plugin_dirs = modules_manager.collect_publish_plugin_paths(
        host_name)
    for path in publish_plugin_dirs:
        pyblish.api.register_plugin_path(path)

    create_plugin_paths = modules_manager.collect_create_plugin_paths(
        host_name)
    for path in create_plugin_paths:
        register_creator_plugin_path(path)

    load_plugin_paths = modules_manager.collect_load_plugin_paths(
        host_name)
    for path in load_plugin_paths:
        register_loader_plugin_path(path)

    inventory_action_paths = modules_manager.collect_inventory_action_paths(
        host_name)
    for path in inventory_action_paths:
        register_inventory_action_path(path)

    if project_name is None:
        project_name = os.environ.get("AVALON_PROJECT")

    # Register studio specific plugins
    if project_name:
        anatomy = Anatomy(project_name)
        anatomy.set_root_environments()
        register_root(anatomy.roots)

        project_settings = get_project_settings(project_name)
        platform_name = platform.system().lower()
        project_plugins = (
            project_settings
            .get("global", {})
            .get("project_plugins", {})
            .get(platform_name)
        ) or []
        for path in project_plugins:
            try:
                path = str(path.format(**os.environ))
            except KeyError:
                pass

            if not path or not os.path.exists(path):
                continue

            pyblish.api.register_plugin_path(path)
            register_loader_plugin_path(path)
            register_creator_plugin_path(path)
            register_inventory_action_path(path)


def uninstall_host():
    """Undo all of what `install()` did"""
    host = registered_host()

    try:
        host.uninstall()
    except AttributeError:
        pass

    log.info("Deregistering global plug-ins..")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    pyblish.api.deregister_discovery_filter(filter_pyblish_plugins)
    deregister_loader_plugin_path(LOAD_PATH)
    deregister_inventory_action_path(INVENTORY_PATH)
    log.info("Global plug-ins unregistred")

    deregister_host()

    legacy_io.uninstall()

    log.info("Successfully uninstalled Avalon!")


def is_installed():
    """Return state of installation

    Returns:
        True if installed, False otherwise

    """

    return _is_installed


def register_host(host):
    """Register a new host for the current process

    Arguments:
        host (ModuleType): A module implementing the
            Host API interface. See the Host API
            documentation for details on what is
            required, or browse the source code.

    """

    _registered_host["_"] = host


def registered_host():
    """Return currently registered host"""
    return _registered_host["_"]


def deregister_host():
    _registered_host["_"] = None


def debug_host():
    """A debug host, useful to debugging features that depend on a host"""

    host = types.ModuleType("debugHost")

    def ls():
        containers = [
            {
                "representation": "ee-ft-a-uuid1",
                "schema": "openpype:container-1.0",
                "name": "Bruce01",
                "objectName": "Bruce01_node",
                "namespace": "_bruce01_",
                "version": 3,
            },
            {
                "representation": "aa-bc-s-uuid2",
                "schema": "openpype:container-1.0",
                "name": "Bruce02",
                "objectName": "Bruce01_node",
                "namespace": "_bruce02_",
                "version": 2,
            }
        ]

        for container in containers:
            yield container

    host.__dict__.update({
        "ls": ls,
        "open_file": lambda fname: None,
        "save_file": lambda fname: None,
        "current_file": lambda: os.path.expanduser("~/temp.txt"),
        "has_unsaved_changes": lambda: False,
        "work_root": lambda: os.path.expanduser("~/temp"),
        "file_extensions": lambda: ["txt"],
    })

    return host


def get_current_host_name():
    """Current host name.

    Function is based on currently registered host integration or environment
    variable 'AVALON_APP'.

    Returns:
        Union[str, None]: Name of host integration in current process or None.
    """

    host = registered_host()
    if isinstance(host, HostBase):
        return host.name
    return os.environ.get("AVALON_APP")


def get_global_context():
    """Global context defined in environment variables.

    Values here may not reflect current context of host integration. The
    function can be used on startup before a host is registered.

    Use 'get_current_context' to make sure you'll get current host integration
    context info.

    Example:
        {
            "project_name": "Commercial",
            "asset_name": "Bunny",
            "task_name": "Animation",
        }

    Returns:
        dict[str, Union[str, None]]: Context defined with environment
            variables.
    """

    return {
        "project_name": os.environ.get("AVALON_PROJECT"),
        "asset_name": os.environ.get("AVALON_ASSET"),
        "task_name": os.environ.get("AVALON_TASK"),
    }


def get_current_context():
    host = registered_host()
    if isinstance(host, HostBase):
        return host.get_current_context()
    return get_global_context()


def get_current_project_name():
    host = registered_host()
    if isinstance(host, HostBase):
        return host.get_current_project_name()
    return get_global_context()["project_name"]


def get_current_asset_name():
    host = registered_host()
    if isinstance(host, HostBase):
        return host.get_current_asset_name()
    return get_global_context()["asset_name"]


def get_current_task_name():
    host = registered_host()
    if isinstance(host, HostBase):
        return host.get_current_task_name()
    return get_global_context()["task_name"]


def get_current_project(fields=None):
    """Helper function to get project document based on global Session.

    This function should be called only in process where host is installed.

    Returns:
        dict: Project document.
        None: Project is not set.
    """

    project_name = get_current_project_name()
    return get_project(project_name, fields=fields)


def get_current_project_asset(asset_name=None, asset_id=None, fields=None):
    """Helper function to get asset document based on global Session.

    This function should be called only in process where host is installed.

    Asset is found out based on passed asset name or id (not both). Asset name
    is not used for filtering if asset id is passed. When both asset name and
    id are missing then asset name from current process is used.

    Args:
        asset_name (str): Name of asset used for filter.
        asset_id (Union[str, ObjectId]): Asset document id. If entered then
            is used as only filter.
        fields (Union[List[str], None]): Limit returned data of asset documents
            to specific keys.

    Returns:
        dict: Asset document.
        None: Asset is not set or not exist.
    """

    project_name = get_current_project_name()
    if asset_id:
        return get_asset_by_id(project_name, asset_id, fields=fields)

    if not asset_name:
        asset_name = get_current_asset_name()
        # Skip if is not set even on context
        if not asset_name:
            return None
    return get_asset_by_name(project_name, asset_name, fields=fields)


def is_representation_from_latest(representation):
    """Return whether the representation is from latest version

    Args:
        representation (dict): The representation document from the database.

    Returns:
        bool: Whether the representation is of latest version.
    """

    project_name = get_current_project_name()
    return version_is_latest(project_name, representation["parent"])


def get_template_data_from_session(session=None, system_settings=None):
    """Template data for template fill from session keys.

    Args:
        session (Union[Dict[str, str], None]): The Session to use. If not
            provided use the currently active global Session.
        system_settings (Union[Dict[str, Any], Any]): Prepared system settings.
            Optional are auto received if not passed.

    Returns:
        Dict[str, Any]: All available data from session.
    """

    if session is None:
        session = legacy_io.Session

    project_name = session["AVALON_PROJECT"]
    asset_name = session["AVALON_ASSET"]
    task_name = session["AVALON_TASK"]
    host_name = session["AVALON_APP"]

    return get_template_data_with_names(
        project_name, asset_name, task_name, host_name, system_settings
    )


def get_current_context_template_data(system_settings=None):
    """Prepare template data for current context.

    Args:
        system_settings (Optional[Dict[str, Any]]): Prepared system settings.

    Returns:
        Dict[str, Any] Template data for current context.
    """

    context = get_current_context()
    project_name = context["project_name"]
    asset_name = context["asset_name"]
    task_name = context["task_name"]
    host_name = get_current_host_name()

    return get_template_data_with_names(
        project_name, asset_name, task_name, host_name, system_settings
    )


def get_workdir_from_session(session=None, template_key=None):
    """Template data for template fill from session keys.

    Args:
        session (Union[Dict[str, str], None]): The Session to use. If not
            provided use the currently active global Session.
        template_key (str): Prepared template key from which workdir is
            calculated.

    Returns:
        str: Workdir path.
    """

    if session is None:
        session = legacy_io.Session
    project_name = session["AVALON_PROJECT"]
    host_name = session["AVALON_APP"]
    template_data = get_template_data_from_session(session)

    if not template_key:
        task_type = template_data["task"]["type"]
        template_key = get_workfile_template_key(
            task_type,
            host_name,
            project_name=project_name
        )

    anatomy = Anatomy(project_name)
    template_obj = anatomy.templates_obj[template_key]["folder"]
    path = template_obj.format_strict(template_data)
    if path:
        path = os.path.normpath(path)
    return path


def get_custom_workfile_template_from_session(
    session=None, project_settings=None
):
    """Filter and fill workfile template profiles by current context.

    Current context is defined by `legacy_io.Session`. That's why this
    function should be used only inside host where context is set and stable.

    Args:
        session (Union[None, Dict[str, str]]): Session from which are taken
            data.
        project_settings(Dict[str, Any]): Template profiles from settings.

    Returns:
        str: Path to template or None if none of profiles match current
            context. (Existence of formatted path is not validated.)
    """

    if session is None:
        session = legacy_io.Session

    return get_custom_workfile_template_by_string_context(
        session["AVALON_PROJECT"],
        session["AVALON_ASSET"],
        session["AVALON_TASK"],
        session["AVALON_APP"],
        project_settings=project_settings
    )


def compute_session_changes(
    session, asset_doc, task_name, template_key=None
):
    """Compute the changes for a session object on task under asset.

    Function does not change the session object, only returns changes.

    Args:
        session (Dict[str, str]): The initial session to compute changes to.
            This is required for computing the full Work Directory, as that
            also depends on the values that haven't changed.
        asset_doc (Dict[str, Any]): Asset document to switch to.
        task_name (str): Name of task to switch to.
        template_key (Union[str, None]): Prepare workfile template key in
            anatomy templates.

    Returns:
        Dict[str, str]: Changes in the Session dictionary.
    """

    # Get asset document and asset
    if not asset_doc:
        task_name = None
        asset_name = None
    else:
        asset_name = get_asset_name_identifier(asset_doc)

    # Detect any changes compared session
    mapping = {
        "AVALON_ASSET": asset_name,
        "AVALON_TASK": task_name,
    }
    changes = {
        key: value
        for key, value in mapping.items()
        if value != session.get(key)
    }
    if not changes:
        return changes

    # Compute work directory (with the temporary changed session so far)
    changed_session = session.copy()
    changed_session.update(changes)

    workdir = None
    if asset_doc:
        workdir = get_workdir_from_session(
            changed_session, template_key
        )

    changes["AVALON_WORKDIR"] = workdir

    return changes


def change_current_context(asset_doc, task_name, template_key=None):
    """Update active Session to a new task work area.

    This updates the live Session to a different task under asset.

    Args:
        asset_doc (Dict[str, Any]): The asset document to set.
        task_name (str): The task to set under asset.
        template_key (Union[str, None]): Prepared template key to be used for
            workfile template in Anatomy.

    Returns:
        Dict[str, str]: The changed key, values in the current Session.
    """

    changes = compute_session_changes(
        legacy_io.Session,
        asset_doc,
        task_name,
        template_key=template_key
    )

    # Update the Session and environments. Pop from environments all keys with
    # value set to None.
    for key, value in changes.items():
        legacy_io.Session[key] = value
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    data = changes.copy()
    # Convert env keys to human readable keys
    data["project_name"] = legacy_io.Session["AVALON_PROJECT"]
    data["asset_name"] = legacy_io.Session["AVALON_ASSET"]
    data["task_name"] = legacy_io.Session["AVALON_TASK"]

    # Emit session change
    emit_event("taskChanged", data)

    return changes


def get_process_id():
    """Fake process id created on demand using uuid.

    Can be used to create process specific folders in temp directory.

    Returns:
        str: Process id.
    """

    global _process_id
    if _process_id is None:
        _process_id = str(uuid.uuid4())
    return _process_id
