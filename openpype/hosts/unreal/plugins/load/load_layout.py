# -*- coding: utf-8 -*-
"""Loader for layouts."""
import os
import json
from pathlib import Path

import unreal
from unreal import EditorAssetLibrary
from unreal import EditorLevelLibrary
from unreal import AssetToolsHelpers
from unreal import FBXImportType
from unreal import MathLibrary as umath

from avalon import api, pipeline
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline


class LayoutLoader(plugin.Loader):
    """Load Layout from a JSON file"""

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout"
    icon = "code-fork"
    color = "orange"
    ASSET_ROOT = "/Game/OpenPype/Assets"

    def _get_asset_containers(self, path):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        asset_content = EditorAssetLibrary.list_assets(
            path, recursive=True)

        asset_containers = []

        # Get all the asset containers
        for a in asset_content:
            obj = ar.get_asset_by_object_path(a)
            if obj.get_asset().get_class().get_name() == 'AssetContainer':
                asset_containers.append(obj)

        return asset_containers

    @staticmethod
    def _get_fbx_loader(loaders, family):
        name = ""
        if family == 'rig':
            name = "SkeletalMeshFBXLoader"
        elif family == 'model':
            name = "StaticMeshFBXLoader"
        elif family == 'camera':
            name = "CameraLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    @staticmethod
    def _get_abc_loader(loaders, family):
        name = ""
        if family == 'rig':
            name = "SkeletalMeshAlembicLoader"
        elif family == 'model':
            name = "StaticMeshAlembicLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    @staticmethod
    def _process_family(assets, class_name, transform, inst_name=None):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        actors = []

        for asset in assets:
            obj = ar.get_asset_by_object_path(asset).get_asset()
            if obj.get_class().get_name() == class_name:
                actor = EditorLevelLibrary.spawn_actor_from_object(
                    obj,
                    transform.get('translation')
                )
                if inst_name:
                    try:
                        # Rename method leads to crash
                        # actor.rename(name=inst_name)

                        # The label works, although it make it slightly more
                        # complicated to check for the names, as we need to
                        # loop through all the actors in the level
                        actor.set_actor_label(inst_name)
                    except Exception as e:
                        print(e)
                actor.set_actor_rotation(unreal.Rotator(
                    umath.radians_to_degrees(
                        transform.get('rotation').get('x')),
                    -umath.radians_to_degrees(
                        transform.get('rotation').get('y')),
                    umath.radians_to_degrees(
                        transform.get('rotation').get('z')),
                ), False)
                actor.set_actor_scale3d(transform.get('scale'))

                actors.append(actor)

        return actors

    @staticmethod
    def _import_animation(
            asset_dir, path, instance_name, skeleton, actors_dict,
            animation_file):
        anim_file = Path(animation_file)
        anim_file_name = anim_file.with_suffix('')

        anim_path = f"{asset_dir}/animations/{anim_file_name}"

        # Import animation
        task = unreal.AssetImportTask()
        task.options = unreal.FbxImportUI()

        task.set_editor_property(
            'filename', str(path.with_suffix(f".{animation_file}")))
        task.set_editor_property('destination_path', anim_path)
        task.set_editor_property(
            'destination_name', f"{instance_name}_animation")
        task.set_editor_property('replace_existing', False)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', False)

        # set import options here
        task.options.set_editor_property(
            'automated_import_should_detect_type', False)
        task.options.set_editor_property(
            'original_import_type', FBXImportType.FBXIT_SKELETAL_MESH)
        task.options.set_editor_property(
            'mesh_type_to_import', FBXImportType.FBXIT_ANIMATION)
        task.options.set_editor_property('import_mesh', False)
        task.options.set_editor_property('import_animations', True)
        task.options.set_editor_property('override_full_name', True)
        task.options.set_editor_property('skeleton', skeleton)

        task.options.anim_sequence_import_data.set_editor_property(
            'animation_length',
            unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME
        )
        task.options.anim_sequence_import_data.set_editor_property(
            'import_meshes_in_bone_hierarchy', False)
        task.options.anim_sequence_import_data.set_editor_property(
            'use_default_sample_rate', True)
        task.options.anim_sequence_import_data.set_editor_property(
            'import_custom_attribute', True)
        task.options.anim_sequence_import_data.set_editor_property(
            'import_bone_tracks', True)
        task.options.anim_sequence_import_data.set_editor_property(
            'remove_redundant_keys', True)
        task.options.anim_sequence_import_data.set_editor_property(
            'convert_scene', True)

        AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        asset_content = unreal.EditorAssetLibrary.list_assets(
            anim_path, recursive=False, include_folder=False
        )

        animation = None

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)
            imported_asset_data = unreal.EditorAssetLibrary.find_asset_data(a)
            imported_asset = unreal.AssetRegistryHelpers.get_asset(
                imported_asset_data)
            if imported_asset.__class__ == unreal.AnimSequence:
                animation = imported_asset
                break

        if animation:
            actor = None
            if actors_dict.get(instance_name):
                for a in actors_dict.get(instance_name):
                    if a.get_class().get_name() == 'SkeletalMeshActor':
                        actor = a
                        break

            animation.set_editor_property('enable_root_motion', True)
            actor.skeletal_mesh_component.set_editor_property(
                'animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            actor.skeletal_mesh_component.animation_data.set_editor_property(
                'anim_to_play', animation)

    def _process(self, lib_path, asset_dir, loaded=None):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        with open(lib_path, "r") as fp:
            data = json.load(fp)

        all_loaders = api.discover(api.Loader)

        if not loaded:
            loaded = []

        path = Path(lib_path)

        skeleton_dict = {}
        actors_dict = {}

        for element in data:
            reference = None
            if element.get('reference_fbx'):
                reference = element.get('reference_fbx')
            elif element.get('reference_abc'):
                reference = element.get('reference_abc')

            # If reference is None, this element is skipped, as it cannot be
            # imported in Unreal
            if not reference:
                continue

            instance_name = element.get('instance_name')

            skeleton = None

            if reference not in loaded:
                loaded.append(reference)

                family = element.get('family')
                loaders = api.loaders_from_representation(
                    all_loaders, reference)

                loader = None

                if reference == element.get('reference_fbx'):
                    loader = self._get_fbx_loader(loaders, family)
                elif reference == element.get('reference_abc'):
                    loader = self._get_abc_loader(loaders, family)

                if not loader:
                    continue

                options = {
                    "asset_dir": asset_dir
                }

                assets = api.load(
                    loader,
                    reference,
                    namespace=instance_name,
                    options=options
                )

                instances = [
                    item for item in data
                    if (item.get('reference_fbx') == reference or
                        item.get('reference_abc') == reference)]

                for instance in instances:
                    transform = instance.get('transform')
                    inst = instance.get('instance_name')

                    actors = []

                    if family == 'model':
                        actors = self._process_family(
                            assets, 'StaticMesh', transform, inst)
                    elif family == 'rig':
                        actors = self._process_family(
                            assets, 'SkeletalMesh', transform, inst)
                        actors_dict[inst] = actors

                if family == 'rig':
                    # Finds skeleton among the imported assets
                    for asset in assets:
                        obj = ar.get_asset_by_object_path(asset).get_asset()
                        if obj.get_class().get_name() == 'Skeleton':
                            skeleton = obj
                            if skeleton:
                                break

                if skeleton:
                    skeleton_dict[reference] = skeleton
            else:
                skeleton = skeleton_dict.get(reference)

            animation_file = element.get('animation')

            if animation_file and skeleton:
                self._import_animation(
                    asset_dir, path, instance_name, skeleton,
                    actors_dict, animation_file)

    @staticmethod
    def _remove_family(assets, components, class_name, prop_name):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        objects = []
        for a in assets:
            obj = ar.get_asset_by_object_path(a)
            if obj.get_asset().get_class().get_name() == class_name:
                objects.append(obj)
        for obj in objects:
            for comp in components:
                if comp.get_editor_property(prop_name) == obj.get_asset():
                    comp.get_owner().destroy_actor()

    def _remove_actors(self, path):
        asset_containers = self._get_asset_containers(path)

        # Get all the static and skeletal meshes components in the level
        components = EditorLevelLibrary.get_all_level_actors_components()
        static_meshes_comp = [
            c for c in components
            if c.get_class().get_name() == 'StaticMeshComponent']
        skel_meshes_comp = [
            c for c in components
            if c.get_class().get_name() == 'SkeletalMeshComponent']

        # For all the asset containers, get the static and skeletal meshes.
        # Then, check the components in the level and destroy the matching
        # actors.
        for asset_container in asset_containers:
            package_path = asset_container.get_editor_property('package_path')
            family = EditorAssetLibrary.get_metadata_tag(
                asset_container.get_asset(), 'family')
            assets = EditorAssetLibrary.list_assets(
                str(package_path), recursive=False)
            if family == 'model':
                self._remove_family(
                    assets, static_meshes_comp, 'StaticMesh', 'static_mesh')
            elif family == 'rig':
                self._remove_family(
                    assets, skel_meshes_comp, 'SkeletalMesh', 'skeletal_mesh')

    def load(self, context, name, namespace, options):
        """Load and containerise representation into Content Browser.

        This is two step process. First, import FBX to temporary path and
        then call `containerise()` on it - this moves all content to new
        directory and then it will create AssetContainer there and imprint it
        with metadata. This will mark this path as container.

        Args:
            context (dict): application context
            name (str): subset name
            namespace (str): in Unreal this is basically path to container.
                             This is not passed here, so namespace is set
                             by `containerise()` because only then we know
                             real path.
            options (dict): Those would be data to be imprinted. This is not
                used now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content
        """
        # Create directory for asset and avalon container
        root = self.ASSET_ROOT
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            "{}/{}/{}".format(root, asset, name), suffix="")

        container_name += suffix

        EditorAssetLibrary.make_directory(asset_dir)

        self._process(self.fname, asset_dir)

        # Create Asset Container
        unreal_pipeline.create_container(
            container=container_name, path=asset_dir)

        data = {
            "schema": "openpype:container-2.0",
            "id": pipeline.AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["_id"],
            "parent": context["representation"]["parent"],
            "family": context["representation"]["context"]["family"]
        }
        unreal_pipeline.imprint(
            "{}/{}".format(asset_dir, container_name), data)

        asset_content = EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=False)

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, representation):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        source_path = api.get_representation_path(representation)
        destination_path = container["namespace"]
        lib_path = Path(api.get_representation_path(representation))

        self._remove_actors(destination_path)

        # Delete old animations
        anim_path = f"{destination_path}/animations/"
        EditorAssetLibrary.delete_directory(anim_path)

        with open(source_path, "r") as fp:
            data = json.load(fp)

        references = [e.get('reference_fbx') for e in data]
        asset_containers = self._get_asset_containers(destination_path)
        loaded = []

        # Delete all the assets imported with the previous version of the
        # layout, if they're not in the new layout.
        for asset_container in asset_containers:
            if asset_container.get_editor_property(
                    'asset_name') == container["objectName"]:
                continue
            ref = EditorAssetLibrary.get_metadata_tag(
                asset_container.get_asset(), 'representation')
            ppath = asset_container.get_editor_property('package_path')

            if ref not in references:
                # If the asset is not in the new layout, delete it.
                # Also check if the parent directory is empty, and delete that
                # as well, if it is.
                EditorAssetLibrary.delete_directory(ppath)

                parent = os.path.dirname(str(ppath))
                parent_content = EditorAssetLibrary.list_assets(
                    parent, recursive=False, include_folder=True
                )

                if len(parent_content) == 0:
                    EditorAssetLibrary.delete_directory(parent)
            else:
                # If the asset is in the new layout, search the instances in
                # the JSON file, and create actors for them.

                actors_dict = {}
                skeleton_dict = {}

                for element in data:
                    reference = element.get('reference_fbx')
                    instance_name = element.get('instance_name')

                    skeleton = None

                    if reference == ref and ref not in loaded:
                        loaded.append(ref)

                        family = element.get('family')

                        assets = EditorAssetLibrary.list_assets(
                            ppath, recursive=True, include_folder=False)

                        instances = [
                            item for item in data
                            if item.get('reference_fbx') == reference]

                        for instance in instances:
                            transform = instance.get('transform')
                            inst = instance.get('instance_name')

                            actors = []

                            if family == 'model':
                                actors = self._process_family(
                                    assets, 'StaticMesh', transform, inst)
                            elif family == 'rig':
                                actors = self._process_family(
                                    assets, 'SkeletalMesh', transform, inst)
                                actors_dict[inst] = actors

                        if family == 'rig':
                            # Finds skeleton among the imported assets
                            for asset in assets:
                                obj = ar.get_asset_by_object_path(
                                    asset).get_asset()
                                if obj.get_class().get_name() == 'Skeleton':
                                    skeleton = obj
                                    if skeleton:
                                        break

                        if skeleton:
                            skeleton_dict[reference] = skeleton
                    else:
                        skeleton = skeleton_dict.get(reference)

                    animation_file = element.get('animation')

                    if animation_file and skeleton:
                        self._import_animation(
                            destination_path, lib_path,
                            instance_name, skeleton,
                            actors_dict, animation_file)

        self._process(source_path, destination_path, loaded)

        container_path = "{}/{}".format(container["namespace"],
                                        container["objectName"])
        # update metadata
        unreal_pipeline.imprint(
            container_path,
            {
                "representation": str(representation["_id"]),
                "parent": str(representation["parent"])
            })

        asset_content = EditorAssetLibrary.list_assets(
            destination_path, recursive=True, include_folder=False)

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

    def remove(self, container):
        """
        First, destroy all actors of the assets to be removed. Then, deletes
        the asset's directory.
        """
        path = container["namespace"]
        parent_path = os.path.dirname(path)

        self._remove_actors(path)

        EditorAssetLibrary.delete_directory(path)

        asset_content = EditorAssetLibrary.list_assets(
            parent_path, recursive=False, include_folder=True
        )

        if len(asset_content) == 0:
            EditorAssetLibrary.delete_directory(parent_path)
