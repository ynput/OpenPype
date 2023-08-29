# -*- coding: utf-8 -*-
import ast
import os
import json
import logging
from contextlib import contextmanager
import semver
import time

import pyblish.api

from openpype.client import get_asset_by_name, get_assets
from openpype.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_creator_plugin_path,
)
from openpype.tools.utils import host_tools
import openpype.hosts.unreal
from openpype.host import HostBase, ILoadHost, IPublishHost
from openpype.hosts.unreal.api.communication_server import (
    CommunicationWrapper
)
logger = logging.getLogger("openpype.hosts.unreal")

AYON_CONTAINERS = "AyonContainers"
CONTEXT_CONTAINER = "Ayon/context.json"
UNREAL_VERSION = semver.VersionInfo(
    *os.getenv("AYON_UNREAL_VERSION").split(".")
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
        content_path = send_request("project_content_dir")

        unreal_log("Updating context data...", "info")

        # The context json will be stored in the OpenPype folder, so we need
        # to create it if it doesn't exist.
        dir_exists = send_request(
            "does_directory_exist",
            params={"directory_path": "/Game/OpenPype"})

        if not dir_exists:
            send_request(
                "make_directory",
                params={"directory_path": "/Game/OpenPype"})

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
                unreal_log(
                    "Failed to write context data. Retrying...", "warning")
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
                    ·
                    │
                   ·∙/
                 ·-∙•∙-·
              / \\  /∙·  / \\
             ∙   \\  │  /   ∙
              \\   \\ · /   /
              \\\\   ∙ ∙  //
                \\\\/   \\//
                   ___
                  │   │
                  │   │
                  │   │
                  │___│
                    -·

         ·-─═─-∙ A Y O N ∙-─═─-·
                by  YNPUT
.
'''
    print(logo)
    print("installing Ayon for Unreal ...")
    print("-=" * 40)
    logger.info("installing Ayon for Unreal")
    pyblish.api.register_host("unreal")
    pyblish.api.register_plugin_path(str(PUBLISH_PATH))
    register_loader_plugin_path(str(LOAD_PATH))
    register_creator_plugin_path(str(CREATE_PATH))
    _register_callbacks()
    _register_events()


def uninstall():
    """Uninstall Unreal configuration for Ayon."""
    pyblish.api.deregister_plugin_path(str(PUBLISH_PATH))
    deregister_loader_plugin_path(str(LOAD_PATH))
    deregister_creator_plugin_path(str(CREATE_PATH))


def _register_callbacks():
    """
    TODO: Implement callbacks if supported by UE
    """
    pass


def _register_events():
    """
    TODO: Implement callbacks if supported by UE
    """
    pass


def send_request(request: str, params: dict = None):
    communicator = CommunicationWrapper.communicator
    if ret_value := ast.literal_eval(
        communicator.send_request(request, params)
    ):
        return ret_value.get("return")
    return None


def unreal_log(message, level):
    """Log message to Unreal.

    Args:
        message (str): message to log
        level (str): level of message

    """
    send_request("log", params={"message": message, "level": level})


def imprint(node, data):
    """Imprint data to container.

    Args:
        node (str): path to container
        data (dict): data to imprint
    """
    send_request("imprint", params={"node": node, "data": data})


def ls():
    """List all containers.

    List all found in *Content Manager* of Unreal and return
    metadata from them. Adding `objectName` to set.

    """
    return send_request("ls")


def ls_inst():
    """List all containers.

    List all found in *Content Manager* of Unreal and return
    metadata from them. Adding `objectName` to set.

    """
    return send_request("ls_inst")


def publish():
    """Shorthand to publish from within host."""
    import pyblish.util

    return pyblish.util.publish()


def containerise(root, name, data, suffix="_CON"):
    """Bundles *nodes* (assets) into a *container* and add metadata to it.

    Unreal doesn't support *groups* of assets that you can add metadata to.
    But it does support folders that helps to organize asset. Unfortunately
    those folders are just that - you cannot add any additional information
    to them. Ayon Integration Plugin is providing way out - Implementing
    `AssetContainer` Blueprint class. This class when added to folder can
    handle metadata on it using standard
    :func:`unreal.EditorAssetLibrary.set_metadata_tag()` and
    :func:`unreal.EditorAssetLibrary.get_metadata_tag_values()`. It also
    stores and monitor all changes in assets in path where it resides. List of
    those assets is available as `assets` property.

    This is list of strings starting with asset type and ending with its path:
    `Material /Game/Ayon/Test/TestMaterial.TestMaterial`

    """
    return send_request(
        "containerise",
        params={
            "root": root,
            "name": name,
            "data": data,
            "suffix": suffix})

def instantiate(root, name, data, assets=None, suffix="_INS"):
    """Bundles *nodes* into *container*.

    Marking it with metadata as publishable instance. If assets are provided,
    they are moved to new path where `AyonPublishInstance` class asset is
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
        "instantiate", params={
            "root": root,
            "name": name,
            "data": data,
            "assets": assets,
            "suffix": suffix})

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
