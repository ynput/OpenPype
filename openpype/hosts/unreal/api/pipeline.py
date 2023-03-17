# -*- coding: utf-8 -*-
import ast
import os
import json
import logging
from typing import List
from contextlib import contextmanager
import semver
import time

import pyblish.api

from openpype.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.tools.utils import host_tools
import openpype.hosts.unreal
from openpype.host import HostBase, ILoadHost, IPublishHost
from openpype.hosts.unreal.api.communication_server import (
    CommunicationWrapper
)

logger = logging.getLogger("openpype.hosts.unreal")

OPENPYPE_CONTAINERS = "OpenPypeContainers"
CONTEXT_CONTAINER = "OpenPype/context.json"
UNREAL_VERSION = semver.VersionInfo(
    *os.getenv("OPENPYPE_UNREAL_VERSION").split(".")
)

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.unreal.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class UnrealHost(HostBase, ILoadHost, IPublishHost):
    """Unreal host implementation.

    For some time this class will re-use functions from module based
    implementation for backwards compatibility of older unreal projects.
    """

    name = "unreal"

    def install(self):
        install()

    def get_containers(self):
        return ls()

    def update_context_data(self, data, changes):
        content_path = send_request_literal("project_content_dir")

        # The context json will be stored in the OpenPype folder, so we need
        # to create it if it doesn't exist.
        if not send_request_literal(
                "does_directory_exist", params=["/Game/OpenPype"]):
            send_request("make_directory", params=["/Game/OpenPype"])

        op_ctx = content_path + CONTEXT_CONTAINER
        attempts = 3
        for i in range(attempts):
            try:
                with open(op_ctx, "w+") as f:
                    json.dump(data, f)
                break
            except IOError as e:
                if i == attempts - 1:
                    raise IOError(
                        "Failed to write context data. Aborting.") from e
                send_request(
                    "log",
                    params=[
                        "Failed to write context data. Retrying...",
                        "warning"])
                i += 1
                time.sleep(3)
                continue

    def get_context_data(self):
        content_path = send_request("project_content_dir")
        op_ctx = content_path + CONTEXT_CONTAINER
        if not os.path.isfile(op_ctx):
            return {}
        with open(op_ctx, "r") as fp:
            data = json.load(fp)
        return data


def install():
    """Install Unreal configuration for OpenPype."""
    print("-=" * 40)
    logo = '''.
.
     ____________
   / \\      __   \\
   \\  \\     \\/_\\  \\
    \\  \\     _____/ ______
     \\  \\    \\___// \\     \\
      \\  \\____\\   \\  \\_____\\
       \\/_____/    \\/______/  PYPE Club .
.
'''
    print(logo)
    print("installing OpenPype for Unreal ...")
    print("-=" * 40)
    logger.info("installing OpenPype for Unreal")
    pyblish.api.register_host("unreal")
    pyblish.api.register_plugin_path(str(PUBLISH_PATH))
    register_loader_plugin_path(str(LOAD_PATH))
    register_creator_plugin_path(str(CREATE_PATH))
    _register_callbacks()
    _register_events()


def uninstall():
    """Uninstall Unreal configuration for Avalon."""
    pyblish.api.deregister_plugin_path(str(PUBLISH_PATH))
    deregister_loader_plugin_path(str(LOAD_PATH))
    deregister_creator_plugin_path(str(CREATE_PATH))


def _register_callbacks():
    """
    TODO: Implement callbacks if supported by UE4
    """
    pass


def _register_events():
    """
    TODO: Implement callbacks if supported by UE4
    """
    pass


def format_string(input):
    string = input.replace('\\', '/')
    string = string.replace('"', '\\"')
    string = string.replace("'", "\\'")
    return f'"{string}"'


def send_request(request, params=None):
    communicator = CommunicationWrapper.communicator
    formatted_params = []
    if params:
        for p in params:
            if isinstance(p, str):
                p = format_string(p)
            formatted_params.append(p)
    return communicator.send_request(request, formatted_params)


def send_request_literal(request, params=None):
    return ast.literal_eval(send_request(request, params))


def ls():
    """List all containers.

    List all found in *Content Manager* of Unreal and return
    metadata from them. Adding `objectName` to set.

    """
    return send_request_literal("ls")


def ls_inst():
    """List all containers.

    List all found in *Content Manager* of Unreal and return
    metadata from them. Adding `objectName` to set.

    """
    return send_request_literal("ls_inst")


def publish():
    """Shorthand to publish from within host."""
    import pyblish.util

    return pyblish.util.publish()


def containerise(name, namespace, nodes, context, loader=None, suffix="_CON"):
    """Bundles *nodes* (assets) into a *container* and add metadata to it.

    Unreal doesn't support *groups* of assets that you can add metadata to.
    But it does support folders that helps to organize asset. Unfortunately
    those folders are just that - you cannot add any additional information
    to them. OpenPype Integration Plugin is providing way out - Implementing
    `AssetContainer` Blueprint class. This class when added to folder can
    handle metadata on it using standard
    :func:`unreal.EditorAssetLibrary.set_metadata_tag()` and
    :func:`unreal.EditorAssetLibrary.get_metadata_tag_values()`. It also
    stores and monitor all changes in assets in path where it resides. List of
    those assets is available as `assets` property.

    This is list of strings starting with asset type and ending with its path:
    `Material /Game/OpenPype/Test/TestMaterial.TestMaterial`

    """
    return send_request(
        "containerise", [name, namespace, nodes, context, loader, suffix])


def instantiate(root, name, data, assets=None, suffix="_INS"):
    """Bundles *nodes* into *container*.

    Marking it with metadata as publishable instance. If assets are provided,
    they are moved to new path where `OpenPypePublishInstance` class asset is
    created and imprinted with metadata.

    This can then be collected for publishing by Pyblish for example.

    Args:
        root (str): root path where to create instance container
        name (str): name of the container
        data (dict): data to imprint on container
        assets (list of str): list of asset paths to include in publish
                              instance
        suffix (str): suffix string to append to instance name

    """
    return send_request(
        "instantiate", params=[root, name, data, assets, suffix])


def show_creator():
    host_tools.show_creator()


def show_loader():
    host_tools.show_loader(use_context=True)


def show_publisher():
    host_tools.show_publish()


def show_manager():
    host_tools.show_scene_inventory()


def show_experimental_tools():
    host_tools.show_experimental_tools_dialog()


@contextmanager
def maintained_selection():
    """Stub to be either implemented or replaced.
    This is needed for old publisher implementation, but
    it is not supported (yet) in UE.
    """
    try:
        yield
    finally:
        pass
