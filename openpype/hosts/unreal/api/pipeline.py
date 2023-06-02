# -*- coding: utf-8 -*-
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
    AYON_CONTAINER_ID,
)
from openpype.tools.utils import host_tools
import openpype.hosts.unreal
from openpype.host import HostBase, ILoadHost, IPublishHost

import unreal  # noqa

# Rename to Ayon once parent module renames
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

    @staticmethod
    def show_tools_popup():
        """Show tools popup with actions leading to show other tools."""
        show_tools_popup()

    @staticmethod
    def show_tools_dialog():
        """Show tools dialog with actions leading to show other tools."""
        show_tools_dialog()

    def update_context_data(self, data, changes):
        content_path = unreal.Paths.project_content_dir()
        op_ctx = content_path + CONTEXT_CONTAINER
        attempts = 3
        for i in range(attempts):
            try:
                with open(op_ctx, "w+") as f:
                    json.dump(data, f)
                break
            except IOError as e:
                if i == attempts - 1:
                    raise Exception(
                        "Failed to write context data. Aborting.") from e
                unreal.log_warning("Failed to write context data. Retrying...")
                i += 1
                time.sleep(3)
                continue

    def get_context_data(self):
        content_path = unreal.Paths.project_content_dir()
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


def ls():
    """List all containers.

    List all found in *Content Manager* of Unreal and return
    metadata from them. Adding `objectName` to set.

    """
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    # UE 5.1 changed how class name is specified
    class_name = ["/Script/Ayon", "AyonAssetContainer"] if UNREAL_VERSION.major == 5 and UNREAL_VERSION.minor > 0 else "AyonAssetContainer"  # noqa
    ayon_containers = ar.get_assets_by_class(class_name, True)

    # get_asset_by_class returns AssetData. To get all metadata we need to
    # load asset. get_tag_values() work only on metadata registered in
    # Asset Registry Project settings (and there is no way to set it with
    # python short of editing ini configuration file).
    for asset_data in ayon_containers:
        asset = asset_data.get_asset()
        data = unreal.EditorAssetLibrary.get_metadata_tag_values(asset)
        data["objectName"] = asset_data.asset_name
        yield cast_map_to_str_dict(data)


def ls_inst():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    # UE 5.1 changed how class name is specified
    class_name = [
        "/Script/Ayon",
        "AyonPublishInstance"
    ] if (
            UNREAL_VERSION.major == 5
            and UNREAL_VERSION.minor > 0
    ) else "AyonPublishInstance"  # noqa
    instances = ar.get_assets_by_class(class_name, True)

    # get_asset_by_class returns AssetData. To get all metadata we need to
    # load asset. get_tag_values() work only on metadata registered in
    # Asset Registry Project settings (and there is no way to set it with
    # python short of editing ini configuration file).
    for asset_data in instances:
        asset = asset_data.get_asset()
        data = unreal.EditorAssetLibrary.get_metadata_tag_values(asset)
        data["objectName"] = asset_data.asset_name
        yield cast_map_to_str_dict(data)


def parse_container(container):
    """To get data from container, AyonAssetContainer must be loaded.

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
    # 1 - create directory for container
    root = "/Game"
    container_name = f"{name}{suffix}"
    new_name = move_assets_to_path(root, container_name, nodes)

    # 2 - create Asset Container there
    path = f"{root}/{new_name}"
    create_container(container=container_name, path=path)

    namespace = path

    data = {
        "schema": "ayon:container-2.0",
        "id": AYON_CONTAINER_ID,
        "name": new_name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": context["representation"]["_id"],
    }
    # 3 - imprint data
    imprint(f"{path}/{container_name}", data)
    return path


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
    container_name = f"{name}{suffix}"

    # if we specify assets, create new folder and move them there. If not,
    # just create empty folder
    if assets:
        new_name = move_assets_to_path(root, container_name, assets)
    else:
        new_name = create_folder(root, name)

    path = f"{root}/{new_name}"
    create_publish_instance(instance=container_name, path=path)

    imprint(f"{path}/{container_name}", data)


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

    with unreal.ScopedEditorTransaction("Ayon containerising"):
        unreal.EditorAssetLibrary.save_asset(node)


def show_tools_popup():
    """Show popup with tools.

    Popup will disappear on click or losing focus.
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
        if eal.does_directory_exist(f"{root}/{name}"):
            name = f"{name}{index}"
            index += 1
        else:
            eal.make_directory(f"{root}/{name}")
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
        eal.rename_asset(asset, f"{root}/{name}/{loaded.get_name()}")

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
    factory = unreal.AyonAssetContainerFactory()
    tools = unreal.AssetToolsHelpers().get_asset_tools()

    return tools.create_asset(container, path, None, factory)


def create_publish_instance(instance: str, path: str) -> unreal.Object:
    """Helper function to create Ayon Publish Instance on given path.

    This behaves similarly as :func:`create_ayon_container`.

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
    factory = unreal.AyonPublishInstanceFactory()
    tools = unreal.AssetToolsHelpers().get_asset_tools()
    return tools.create_asset(instance, path, None, factory)


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
    subscene_track = next(
        (
            t
            for t in tracks
            if t.get_class() == unreal.MovieSceneSubTrack.static_class()
        ),
        None,
    )
    if subscene_track is not None and subscene_track.get_sections():
        return subscene_track.get_sections()
    return []


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
