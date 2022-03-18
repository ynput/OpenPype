# -*- coding: utf-8 -*-
"""Load FBX with animations."""
import os
import json

import unreal
from unreal import EditorAssetLibrary
from unreal import MovieSceneSkeletalAnimationTrack
from unreal import MovieSceneSkeletalAnimationSection

from avalon import pipeline
from openpype.pipeline import get_representation_path
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline


class AnimationFBXLoader(plugin.Loader):
    """Load Unreal SkeletalMesh from FBX."""

    families = ["animation"]
    label = "Import FBX Animation"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def _process(self, asset_dir, asset_name, instance_name):
        automated = False
        actor = None

        task = unreal.AssetImportTask()
        task.options = unreal.FbxImportUI()

        if instance_name:
            automated = True
            # Old method to get the actor
            # actor_name = 'PersistentLevel.' + instance_name
            # actor = unreal.EditorLevelLibrary.get_actor_reference(actor_name)
            actors = unreal.EditorLevelLibrary.get_all_level_actors()
            for a in actors:
                if a.get_class().get_name() != "SkeletalMeshActor":
                    continue
                if a.get_actor_label() == instance_name:
                    actor = a
                    break
            if not actor:
                raise Exception(f"Could not find actor {instance_name}")
            skeleton = actor.skeletal_mesh_component.skeletal_mesh.skeleton
            task.options.set_editor_property('skeleton', skeleton)

        if not actor:
            return None

        task.set_editor_property('filename', self.fname)
        task.set_editor_property('destination_path', asset_dir)
        task.set_editor_property('destination_name', asset_name)
        task.set_editor_property('replace_existing', False)
        task.set_editor_property('automated', automated)
        task.set_editor_property('save', False)

        # set import options here
        task.options.set_editor_property(
            'automated_import_should_detect_type', False)
        task.options.set_editor_property(
            'original_import_type', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        task.options.set_editor_property(
            'mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
        task.options.set_editor_property('import_mesh', False)
        task.options.set_editor_property('import_animations', True)
        task.options.set_editor_property('override_full_name', True)

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

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        asset_content = EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=True
        )

        animation = None

        for a in asset_content:
            imported_asset_data = EditorAssetLibrary.find_asset_data(a)
            imported_asset = unreal.AssetRegistryHelpers.get_asset(
                imported_asset_data)
            if imported_asset.__class__ == unreal.AnimSequence:
                animation = imported_asset
                break

        if animation:
            animation.set_editor_property('enable_root_motion', True)
            actor.skeletal_mesh_component.set_editor_property(
                'animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            actor.skeletal_mesh_component.animation_data.set_editor_property(
                'anim_to_play', animation)

        return animation

    def load(self, context, name, namespace, options=None):
        """
        Load and containerise representation into Content Browser.

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
            data (dict): Those would be data to be imprinted. This is not used
                         now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content
        """

        # Create directory for asset and avalon container
        hierarchy = context.get('asset').get('data').get('parents')
        root = "/Game/OpenPype"
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            f"{root}/Animations/{asset}/{name}", suffix="")

        hierarchy_dir = root
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
        hierarchy_dir = f"{hierarchy_dir}/{asset}"

        container_name += suffix

        EditorAssetLibrary.make_directory(asset_dir)

        libpath = self.fname.replace("fbx", "json")

        with open(libpath, "r") as fp:
            data = json.load(fp)

        instance_name = data.get("instance_name")

        animation = self._process(asset_dir, container_name, instance_name)

        asset_content = EditorAssetLibrary.list_assets(
            hierarchy_dir, recursive=True, include_folder=False)

        # Get the sequence for the layout, excluding the camera one.
        sequences = [a for a in asset_content
                     if (EditorAssetLibrary.find_asset_data(a).get_class() ==
                         unreal.LevelSequence.static_class() and
                         "_camera" not in a.split("/")[-1])]

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        for s in sequences:
            sequence = ar.get_asset_by_object_path(s).get_asset()
            possessables = [
                p for p in sequence.get_possessables()
                if p.get_display_name() == instance_name]

            for p in possessables:
                tracks = [
                    t for t in p.get_tracks()
                    if (t.get_class() ==
                        MovieSceneSkeletalAnimationTrack.static_class())]

                for t in tracks:
                    sections = [
                        s for s in t.get_sections()
                        if (s.get_class() ==
                            MovieSceneSkeletalAnimationSection.static_class())]

                    for s in sections:
                        s.params.set_editor_property('animation', animation)

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

        imported_content = EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=False)

        for a in imported_content:
            EditorAssetLibrary.save_asset(a)

    def update(self, container, representation):
        name = container["asset_name"]
        source_path = get_representation_path(representation)
        destination_path = container["namespace"]

        task = unreal.AssetImportTask()
        task.options = unreal.FbxImportUI()

        task.set_editor_property('filename', source_path)
        task.set_editor_property('destination_path', destination_path)
        # strip suffix
        task.set_editor_property('destination_name', name)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)

        # set import options here
        task.options.set_editor_property(
            'automated_import_should_detect_type', False)
        task.options.set_editor_property(
            'original_import_type', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        task.options.set_editor_property(
            'mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
        task.options.set_editor_property('import_mesh', False)
        task.options.set_editor_property('import_animations', True)
        task.options.set_editor_property('override_full_name', True)

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

        skeletal_mesh = EditorAssetLibrary.load_asset(
            container.get('namespace') + "/" + container.get('asset_name'))
        skeleton = skeletal_mesh.get_editor_property('skeleton')
        task.options.set_editor_property('skeleton', skeleton)

        # do import fbx and replace existing data
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
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
            destination_path, recursive=True, include_folder=True
        )

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

    def remove(self, container):
        path = container["namespace"]
        parent_path = os.path.dirname(path)

        EditorAssetLibrary.delete_directory(path)

        asset_content = EditorAssetLibrary.list_assets(
            parent_path, recursive=False, include_folder=True
        )

        if len(asset_content) == 0:
            EditorAssetLibrary.delete_directory(parent_path)
