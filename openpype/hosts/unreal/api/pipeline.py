# -*- coding: utf-8 -*-
import os
import json
import logging
from typing import List
from contextlib import contextmanager
import semver
import time

import pyblish.api

from openpype.client import get_asset_by_name, get_assets
from openpype.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    register_inventory_action_path,
    deregister_loader_plugin_path,
    deregister_creator_plugin_path,
    deregister_inventory_action_path,
    AYON_CONTAINER_ID,
    legacy_io,
)
from openpype.tools.utils import host_tools
import openpype.hosts.unreal
from openpype.host import HostBase, ILoadHost, IPublishHost

import unreal  # noqa

# Rename to Ayon once parent module renames
logger = logging.getLogger("openpype.hosts.unreal")

AYON_CONTAINERS = "AyonContainers"
AYON_ASSET_DIR = "/Game/Ayon/Assets"
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
    register_inventory_action_path(str(INVENTORY_PATH))
    _register_callbacks()
    _register_events()


def uninstall():
    """Uninstall Unreal configuration for Ayon."""
    pyblish.api.deregister_plugin_path(str(PUBLISH_PATH))
    deregister_loader_plugin_path(str(LOAD_PATH))
    deregister_creator_plugin_path(str(CREATE_PATH))
    deregister_inventory_action_path(str(INVENTORY_PATH))


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


def set_sequence_hierarchy(
    seq_i, seq_j, max_frame_i, min_frame_j, max_frame_j, map_paths
):
    # Get existing sequencer tracks or create them if they don't exist
    tracks = seq_i.get_master_tracks()
    subscene_track = None
    visibility_track = None
    for t in tracks:
        if t.get_class() == unreal.MovieSceneSubTrack.static_class():
            subscene_track = t
        if (t.get_class() ==
                unreal.MovieSceneLevelVisibilityTrack.static_class()):
            visibility_track = t
    if not subscene_track:
        subscene_track = seq_i.add_master_track(unreal.MovieSceneSubTrack)
    if not visibility_track:
        visibility_track = seq_i.add_master_track(
            unreal.MovieSceneLevelVisibilityTrack)

    # Create the sub-scene section
    subscenes = subscene_track.get_sections()
    subscene = None
    for s in subscenes:
        if s.get_editor_property('sub_sequence') == seq_j:
            subscene = s
            break
    if not subscene:
        subscene = subscene_track.add_section()
        subscene.set_row_index(len(subscene_track.get_sections()))
        subscene.set_editor_property('sub_sequence', seq_j)
        subscene.set_range(
            min_frame_j,
            max_frame_j + 1)

    # Create the visibility section
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    maps = []
    for m in map_paths:
        # Unreal requires to load the level to get the map name
        unreal.EditorLevelLibrary.save_all_dirty_levels()
        unreal.EditorLevelLibrary.load_level(m)
        maps.append(str(ar.get_asset_by_object_path(m).asset_name))

    vis_section = visibility_track.add_section()
    index = len(visibility_track.get_sections())

    vis_section.set_range(
        min_frame_j,
        max_frame_j + 1)
    vis_section.set_visibility(unreal.LevelVisibility.VISIBLE)
    vis_section.set_row_index(index)
    vis_section.set_level_names(maps)

    if min_frame_j > 1:
        hid_section = visibility_track.add_section()
        hid_section.set_range(
            1,
            min_frame_j)
        hid_section.set_visibility(unreal.LevelVisibility.HIDDEN)
        hid_section.set_row_index(index)
        hid_section.set_level_names(maps)
    if max_frame_j < max_frame_i:
        hid_section = visibility_track.add_section()
        hid_section.set_range(
            max_frame_j + 1,
            max_frame_i + 1)
        hid_section.set_visibility(unreal.LevelVisibility.HIDDEN)
        hid_section.set_row_index(index)
        hid_section.set_level_names(maps)


def generate_sequence(h, h_dir):
    tools = unreal.AssetToolsHelpers().get_asset_tools()

    sequence = tools.create_asset(
        asset_name=h,
        package_path=h_dir,
        asset_class=unreal.LevelSequence,
        factory=unreal.LevelSequenceFactoryNew()
    )

    project_name = legacy_io.active_project()
    asset_data = get_asset_by_name(
        project_name,
        h_dir.split('/')[-1],
        fields=["_id", "data.fps"]
    )

    start_frames = []
    end_frames = []

    elements = list(get_assets(
        project_name,
        parent_ids=[asset_data["_id"]],
        fields=["_id", "data.clipIn", "data.clipOut"]
    ))
    for e in elements:
        start_frames.append(e.get('data').get('clipIn'))
        end_frames.append(e.get('data').get('clipOut'))

        elements.extend(get_assets(
            project_name,
            parent_ids=[e["_id"]],
            fields=["_id", "data.clipIn", "data.clipOut"]
        ))

    min_frame = min(start_frames)
    max_frame = max(end_frames)

    fps = asset_data.get('data').get("fps")

    sequence.set_display_rate(
        unreal.FrameRate(fps, 1.0))
    sequence.set_playback_start(min_frame)
    sequence.set_playback_end(max_frame)

    sequence.set_work_range_start(min_frame / fps)
    sequence.set_work_range_end(max_frame / fps)
    sequence.set_view_range_start(min_frame / fps)
    sequence.set_view_range_end(max_frame / fps)

    tracks = sequence.get_master_tracks()
    track = None
    for t in tracks:
        if (t.get_class() ==
                unreal.MovieSceneCameraCutTrack.static_class()):
            track = t
            break
    if not track:
        track = sequence.add_master_track(
            unreal.MovieSceneCameraCutTrack)

    return sequence, (min_frame, max_frame)


def _get_comps_and_assets(
    component_class, asset_class, old_assets, new_assets, selected
):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    components = []
    if selected:
        sel_actors = eas.get_selected_level_actors()
        for actor in sel_actors:
            comps = actor.get_components_by_class(component_class)
            components.extend(comps)
    else:
        comps = eas.get_all_level_actors_components()
        components = [
            c for c in comps if isinstance(c, component_class)
        ]

    # Get all the static meshes among the old assets in a dictionary with
    # the name as key
    selected_old_assets = {}
    for a in old_assets:
        asset = unreal.EditorAssetLibrary.load_asset(a)
        if isinstance(asset, asset_class):
            selected_old_assets[asset.get_name()] = asset

    # Get all the static meshes among the new assets in a dictionary with
    # the name as key
    selected_new_assets = {}
    for a in new_assets:
        asset = unreal.EditorAssetLibrary.load_asset(a)
        if isinstance(asset, asset_class):
            selected_new_assets[asset.get_name()] = asset

    return components, selected_old_assets, selected_new_assets


def replace_static_mesh_actors(old_assets, new_assets, selected):
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)

    static_mesh_comps, old_meshes, new_meshes = _get_comps_and_assets(
        unreal.StaticMeshComponent,
        unreal.StaticMesh,
        old_assets,
        new_assets,
        selected
    )

    for old_name, old_mesh in old_meshes.items():
        new_mesh = new_meshes.get(old_name)

        if not new_mesh:
            continue

        smes.replace_mesh_components_meshes(
            static_mesh_comps, old_mesh, new_mesh)


def replace_skeletal_mesh_actors(old_assets, new_assets, selected):
    skeletal_mesh_comps, old_meshes, new_meshes = _get_comps_and_assets(
        unreal.SkeletalMeshComponent,
        unreal.SkeletalMesh,
        old_assets,
        new_assets,
        selected
    )

    for old_name, old_mesh in old_meshes.items():
        new_mesh = new_meshes.get(old_name)

        if not new_mesh:
            continue

        for comp in skeletal_mesh_comps:
            if comp.get_skeletal_mesh_asset() == old_mesh:
                comp.set_skeletal_mesh_asset(new_mesh)


def replace_geometry_cache_actors(old_assets, new_assets, selected):
    geometry_cache_comps, old_caches, new_caches = _get_comps_and_assets(
        unreal.GeometryCacheComponent,
        unreal.GeometryCache,
        old_assets,
        new_assets,
        selected
    )

    for old_name, old_mesh in old_caches.items():
        new_mesh = new_caches.get(old_name)

        if not new_mesh:
            continue

        for comp in geometry_cache_comps:
            if comp.get_editor_property("geometry_cache") == old_mesh:
                comp.set_geometry_cache(new_mesh)


def delete_asset_if_unused(container, asset_content):
    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    references = set()

    for asset_path in asset_content:
        asset = ar.get_asset_by_object_path(asset_path)
        refs = ar.get_referencers(
            asset.package_name,
            unreal.AssetRegistryDependencyOptions(
                include_soft_package_references=False,
                include_hard_package_references=True,
                include_searchable_names=False,
                include_soft_management_references=False,
                include_hard_management_references=False
            ))
        if not refs:
            continue
        references = references.union(set(refs))

    # Filter out references that are in the Temp folder
    cleaned_references = {
        ref for ref in references if not str(ref).startswith("/Temp/")}

    # Check which of the references are Levels
    for ref in cleaned_references:
        loaded_asset = unreal.EditorAssetLibrary.load_asset(ref)
        if isinstance(loaded_asset, unreal.World):
            # If there is at least a level, we can stop, we don't want to
            # delete the container
            return

    unreal.log("Previous version unused, deleting...")

    # No levels, delete the asset
    unreal.EditorAssetLibrary.delete_directory(container["namespace"])


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
