"""Core pipeline functionality"""

import os
import sys
import json
import types
import logging
import inspect
import platform

import pyblish.api
from pyblish.lib import MessageHandler

import openpype
from openpype.modules import load_modules
from openpype.settings import get_project_settings
from openpype.lib import (
    Anatomy,
    register_event_callback,
    filter_pyblish_plugins,
    change_timer_to_current_context,
)

from . import (
    legacy_io,
    register_loader_plugin_path,
    register_inventory_action,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
)


_is_installed = False
_registered_root = {"_": ""}
_registered_host = {"_": None}

log = logging.getLogger(__name__)

PACKAGE_DIR = os.path.dirname(os.path.abspath(openpype.__file__))
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")


def register_root(path):
    """Register currently active root"""
    log.info("Registering root: %s" % path)
    _registered_root["_"] = path


def registered_root():
    """Return currently registered root"""
    root = _registered_root["_"]
    if root:
        return root

    root = legacy_io.Session.get("AVALON_PROJECTS")
    if root:
        return os.path.normpath(root)
    return ""


def install_host(host):
    """Install `host` into the running Python session.

    Args:
        host (module): A Python module containing the Avalon
            avalon host-interface.
    """
    global _is_installed

    _is_installed = True

    legacy_io.install()

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

    register_event_callback("taskChanged", _on_task_change)

    def modified_emit(obj, record):
        """Method replacing `emit` in Pyblish's MessageHandler."""
        record.msg = record.getMessage()
        obj.records.append(record)

    MessageHandler.emit = modified_emit

    install_openpype_plugins()


def install_openpype_plugins(project_name=None):
    # Make sure modules are loaded
    load_modules()

    log.info("Registering global plug-ins..")
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    pyblish.api.register_discovery_filter(filter_pyblish_plugins)
    register_loader_plugin_path(LOAD_PATH)

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
            register_inventory_action(path)


def _on_task_change():
    change_timer_to_current_context()


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
    signatures = {
        "ls": []
    }

    _validate_signature(host, signatures)
    _registered_host["_"] = host


def _validate_signature(module, signatures):
    # Required signatures for each member

    missing = list()
    invalid = list()
    success = True

    for member in signatures:
        if not hasattr(module, member):
            missing.append(member)
            success = False

        else:
            attr = getattr(module, member)
            if sys.version_info.major >= 3:
                signature = inspect.getfullargspec(attr)[0]
            else:
                signature = inspect.getargspec(attr)[0]
            required_signature = signatures[member]

            assert isinstance(signature, list)
            assert isinstance(required_signature, list)

            if not all(member in signature
                       for member in required_signature):
                invalid.append({
                    "member": member,
                    "signature": ", ".join(signature),
                    "required": ", ".join(required_signature)
                })
                success = False

    if not success:
        report = list()

        if missing:
            report.append(
                "Incomplete interface for module: '%s'\n"
                "Missing: %s" % (module, ", ".join(
                    "'%s'" % member for member in missing))
            )

        if invalid:
            report.append(
                "'%s': One or more members were found, but didn't "
                "have the right argument signature." % module.__name__
            )

            for member in invalid:
                report.append(
                    "     Found: {member}({signature})".format(**member)
                )
                report.append(
                    "  Expected: {member}({required})".format(**member)
                )

        raise ValueError("\n".join(report))


def registered_host():
    """Return currently registered host"""
    return _registered_host["_"]


def deregister_host():
    _registered_host["_"] = default_host()


def default_host():
    """A default host, in place of anything better

    This may be considered as reference for the
    interface a host must implement. It also ensures
    that the system runs, even when nothing is there
    to support it.

    """

    host = types.ModuleType("defaultHost")

    def ls():
        return list()

    host.__dict__.update({
        "ls": ls
    })

    return host


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
