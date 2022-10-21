# -*- coding: utf-8 -*-
import ast
import os
import logging
from typing import List

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
from openpype.host import HostBase, ILoadHost
from openpype.hosts.unreal.api.communication_server import (
    CommunicationWrapper
)


logger = logging.getLogger("openpype.hosts.unreal")
OPENPYPE_CONTAINERS = "OpenPypeContainers"

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.unreal.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class UnrealHost(HostBase, ILoadHost):
    """Unreal host implementation.

    For some time this class will re-use functions from module based
    implementation for backwards compatibility of older unreal projects.
    """

    name = "unreal"

    def install(self):
        install()

    def get_containers(self):
        return ls()


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


def ls():
    """List all containers.

    List all found in *Content Manager* of Unreal and return
    metadata from them. Adding `objectName` to set.

    """
    communicator = CommunicationWrapper.communicator
    return ast.literal_eval(communicator.send_request("ls"))


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
    communicator = CommunicationWrapper.communicator
    return communicator.send_request(
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
    communicator = CommunicationWrapper.communicator
    return communicator.send_request(
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
