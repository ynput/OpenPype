# -*- coding: utf-8 -*-
import os
import logging
from typing import List

import pyblish.api
from avalon.pipeline import AVALON_CONTAINER_ID
from avalon import api

from openpype.pipeline import (
    LegacyCreator,
    register_loader_plugin_path,
    deregister_loader_plugin_path,
)
from openpype.tools.utils import host_tools
import openpype.hosts.unreal

import unreal  # noqa


logger = logging.getLogger("openpype.hosts.unreal")
OPENPYPE_CONTAINERS = "OpenPypeContainers"

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.unreal.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


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
    api.register_plugin_path(LegacyCreator, str(CREATE_PATH))
    _register_callbacks()
    _register_events()


def uninstall():
    """Uninstall Unreal configuration for Avalon."""
    pyblish.api.deregister_plugin_path(str(PUBLISH_PATH))
    deregister_loader_plugin_path(str(LOAD_PATH))
    api.deregister_plugin_path(LegacyCreator, str(CREATE_PATH))


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


class Creator(LegacyCreator):
    hosts = ["unreal"]
    asset_types = []

    def process(self):
        nodes = list()

        with unreal.ScopedEditorTransaction("OpenPype Creating Instance"):
            if (self.options or {}).get("useSelection"):
                self.log.info("setting ...")
                print("settings ...")
                nodes = unreal.EditorUtilityLibrary.get_selected_assets()

                asset_paths = [a.get_path_name() for a in nodes]
                self.name = move_assets_to_path(
                    "/Game", self.name, asset_paths
                )

            instance = create_publish_instance("/Game", self.name)
            imprint(instance, self.data)

        return instance


def ls():
    """List all containers.

    List all found in *Content Manager* of Unreal and return
    metadata from them. Adding `objectName` to set.

    """
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    openpype_containers = ar.get_assets_by_class("AssetContainer", True)

    # get_asset_by_class returns AssetData. To get all metadata we need to
    # load asset. get_tag_values() work only on metadata registered in
    # Asset Registry Project settings (and there is no way to set it with
    # python short of editing ini configuration file).
    for asset_data in openpype_containers:
        asset = asset_data.get_asset()
        data = unreal.EditorAssetLibrary.get_metadata_tag_values(asset)
        data["objectName"] = asset_data.asset_name
        data = cast_map_to_str_dict(data)

        yield data


def parse_container(container):
    """To get data from container, AssetContainer must be loaded.

    Args:
        container(str): path to container

    Returns:
        dict: metadata stored on container
    """
    asset = unreal.EditorAssetLibrary.load_asset(container)
    data = unreal.EditorAssetLibrary.get_metadata_tag_values(asset)
    data["objectName"] = asset.get_name()
    data = cast_map_to_str_dict(data)

    return data


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
    # 1 - create directory for container
    root = "/Game"
    container_name = "{}{}".format(name, suffix)
    new_name = move_assets_to_path(root, container_name, nodes)

    # 2 - create Asset Container there
    path = "{}/{}".format(root, new_name)
    create_container(container=container_name, path=path)

    namespace = path

    data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": new_name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": context["representation"]["_id"],
    }
    # 3 - imprint data
    imprint("{}/{}".format(path, container_name), data)
    return path


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
    container_name = "{}{}".format(name, suffix)

    # if we specify assets, create new folder and move them there. If not,
    # just create empty folder
    if assets:
        new_name = move_assets_to_path(root, container_name, assets)
    else:
        new_name = create_folder(root, name)

    path = "{}/{}".format(root, new_name)
    create_publish_instance(instance=container_name, path=path)

    imprint("{}/{}".format(path, container_name), data)


def imprint(node, data):
    loaded_asset = unreal.EditorAssetLibrary.load_asset(node)
    for key, value in data.items():
        # Support values evaluated at imprint
        if callable(value):
            value = value()
        # Unreal doesn't support NoneType in metadata values
        if value is None:
            value = ""
        unreal.EditorAssetLibrary.set_metadata_tag(
            loaded_asset, key, str(value)
        )

    with unreal.ScopedEditorTransaction("OpenPype containerising"):
        unreal.EditorAssetLibrary.save_asset(node)


def show_tools_popup():
    """Show popup with tools.

    Popup will disappear on click or loosing focus.
    """
    from openpype.hosts.unreal.api import tools_ui

    tools_ui.show_tools_popup()


def show_tools_dialog():
    """Show dialog with tools.

    Dialog will stay visible.
    """
    from openpype.hosts.unreal.api import tools_ui

    tools_ui.show_tools_dialog()


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


def create_folder(root: str, name: str) -> str:
    """Create new folder.

    If folder exists, append number at the end and try again, incrementing
    if needed.

    Args:
        root (str): path root
        name (str): folder name

    Returns:
        str: folder name

    Example:
        >>> create_folder("/Game/Foo")
        /Game/Foo
        >>> create_folder("/Game/Foo")
        /Game/Foo1

    """
    eal = unreal.EditorAssetLibrary
    index = 1
    while True:
        if eal.does_directory_exist("{}/{}".format(root, name)):
            name = "{}{}".format(name, index)
            index += 1
        else:
            eal.make_directory("{}/{}".format(root, name))
            break

    return name


def move_assets_to_path(root: str, name: str, assets: List[str]) -> str:
    """Moving (renaming) list of asset paths to new destination.

    Args:
        root (str): root of the path (eg. `/Game`)
        name (str): name of destination directory (eg. `Foo` )
        assets (list of str): list of asset paths

    Returns:
        str: folder name

    Example:
        This will get paths of all assets under `/Game/Test` and move them
        to `/Game/NewTest`. If `/Game/NewTest` already exists, then resulting
        path will be `/Game/NewTest1`

        >>> assets = unreal.EditorAssetLibrary.list_assets("/Game/Test")
        >>> move_assets_to_path("/Game", "NewTest", assets)
        NewTest

    """
    eal = unreal.EditorAssetLibrary
    name = create_folder(root, name)

    unreal.log(assets)
    for asset in assets:
        loaded = eal.load_asset(asset)
        eal.rename_asset(
            asset, "{}/{}/{}".format(root, name, loaded.get_name())
        )

    return name


def create_container(container: str, path: str) -> unreal.Object:
    """Helper function to create Asset Container class on given path.

    This Asset Class helps to mark given path as Container
    and enable asset version control on it.

    Args:
        container (str): Asset Container name
        path (str): Path where to create Asset Container. This path should
            point into container folder

    Returns:
        :class:`unreal.Object`: instance of created asset

    Example:

        create_container(
            "/Game/modelingFooCharacter_CON",
            "modelingFooCharacter_CON"
        )

    """
    factory = unreal.AssetContainerFactory()
    tools = unreal.AssetToolsHelpers().get_asset_tools()

    asset = tools.create_asset(container, path, None, factory)
    return asset


def create_publish_instance(instance: str, path: str) -> unreal.Object:
    """Helper function to create OpenPype Publish Instance on given path.

    This behaves similarly as :func:`create_openpype_container`.

    Args:
        path (str): Path where to create Publish Instance.
            This path should point into container folder
        instance (str): Publish Instance name

    Returns:
        :class:`unreal.Object`: instance of created asset

    Example:

        create_publish_instance(
            "/Game/modelingFooCharacter_INST",
            "modelingFooCharacter_INST"
        )

    """
    factory = unreal.OpenPypePublishInstanceFactory()
    tools = unreal.AssetToolsHelpers().get_asset_tools()
    asset = tools.create_asset(instance, path, None, factory)
    return asset


def cast_map_to_str_dict(umap) -> dict:
    """Cast Unreal Map to dict.

    Helper function to cast Unreal Map object to plain old python
    dict. This will also cast values and keys to str. Useful for
    metadata dicts.

    Args:
        umap: Unreal Map object

    Returns:
        dict

    """
    return {str(key): str(value) for (key, value) in umap.items()}


def get_subsequences(sequence: unreal.LevelSequence):
    """Get list of subsequences from sequence.

    Args:
        sequence (unreal.LevelSequence): Sequence

    Returns:
        list(unreal.LevelSequence): List of subsequences

    """
    tracks = sequence.get_master_tracks()
    subscene_track = None
    for t in tracks:
        if t.get_class() == unreal.MovieSceneSubTrack.static_class():
            subscene_track = t
            break
    if subscene_track is not None and subscene_track.get_sections():
        return subscene_track.get_sections()
    return []
