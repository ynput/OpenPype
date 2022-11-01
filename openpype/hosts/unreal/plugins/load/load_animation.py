# -*- coding: utf-8 -*-
"""Load FBX with animations."""
import os
import json

from openpype.pipeline.context_tools import get_current_project_asset
from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as up


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
        skeleton = None

        if instance_name:
            automated = True
            actor, skeleton = up.send_request_literal(
                "get_actor_and_skeleton", params=[instance_name])

        if not actor:
            return None

        asset_doc = get_current_project_asset(fields=["data.fps"])
        fps = asset_doc.get("data", {}).get("fps")

        task_properties = [
            ("filename", up.format_string(self.fname)),
            ("destination_path", up.format_string(asset_dir)),
            ("destination_name", up.format_string(asset_name)),
            ("replace_existing", "False"),
            ("automated", str(automated)),
            ("save", "False")
        ]

        options_properties = [
            ("automated_import_should_detect_type", "False"),
            ("original_import_type",
                "unreal.FBXImportType.FBXIT_SKELETAL_MESH"),
            ("mesh_type_to_import",
                "unreal.FBXImportType.FBXIT_ANIMATION"),
            ("import_mesh", "False"),
            ("import_animations", "True"),
            ("override_full_name", "True"),
            ("skeleton", f"get_asset({up.format_string(skeleton)})")
        ]

        options_extra_properties = [
            ("anim_sequence_import_data", "animation_length",
                "unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME"),
            ("anim_sequence_import_data",
                "import_meshes_in_bone_hierarchy", "False"),
            ("anim_sequence_import_data", "use_default_sample_rate", "False"),
            ("anim_sequence_import_data", "custom_sample_rate", str(fps)),
            ("anim_sequence_import_data", "import_custom_attribute", "True"),
            ("anim_sequence_import_data", "import_bone_tracks", "True"),
            ("anim_sequence_import_data", "remove_redundant_keys", "False"),
            ("anim_sequence_import_data", "convert_scene", "True")
        ]

        up.send_request(
            "import_fbx_task",
            params=[
                str(task_properties),
                str(options_properties),
                str(options_extra_properties)
            ])

        asset_content = up.send_request_literal(
            "list_assets", params=[asset_dir, "True", "True"])

        animation = None

        animations = up.send_request_literal(
            "get_assets_of_class",
            params=[asset_content, "AnimSequence"])
        if animations:
            animation = animations[0]

        if animation:
            up.send_request(
                "apply_animation_to_actor", params=[actor, animation])

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
        asset_name = f"{asset}_{name}" if asset else f"{name}"

        asset_dir, container_name = up.send_request_literal(
            "create_unique_asset_name",
            params=[f"{root}/Animations", asset, name])

        master_level = up.send_request(
            "get_first_asset_of_class",
            params=["World", f"{root}/{hierarchy[0]}", "False"])

        hierarchy_dir = root
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
        hierarchy_dir = f"{hierarchy_dir}/{asset}"

        level = up.send_request(
            "get_first_asset_of_class",
            params=["World", f"{hierarchy_dir}/", "False"])

        up.send_request("save_all_dirty_levels")
        up.send_request("load_level", params=[level])

        container_name += suffix

        up.send_request("make_directory", params=[asset_dir])

        libpath = self.fname.replace("fbx", "json")

        with open(libpath, "r") as fp:
            data = json.load(fp)

        instance_name = data.get("instance_name")

        animation = self._process(asset_dir, asset_name, instance_name)

        asset_content = up.send_request_literal(
            "list_assets", params=[hierarchy_dir, "True", "False"])

        # Get the sequence for the layout, excluding the camera one.
        all_sequences = up.send_request_literal(
            "get_assets_of_class",
            params=[asset_content, "LevelSequence"])
        sequences = [
            a for a in all_sequences
            if "_camera" not in a.split("/")[-1]]

        up.send_request(
            "apply_animation",
            params=[animation, instance_name, str(sequences)])

        # Create Asset Container
        up.send_request(
            "create_container", params=[container_name, asset_dir])

        data = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": str(context["representation"]["_id"]),
            "parent": str(context["representation"]["parent"]),
            "family": context["representation"]["context"]["family"]
        }
        up.send_request(
            "imprint", params=[f"{asset_dir}/{container_name}", str(data)])

        asset_content = up.send_request_literal(
            "list_assets", params=[asset_dir, "True", "False"])

        up.send_request(
            "save_listed_assets", params=[str(asset_content)])

        up.send_request("save_current_level")
        up.send_request("load_level", params=[master_level])

        return asset_content

    # def update(self, container, representation):
    #     name = container["asset_name"]
    #     source_path = get_representation_path(representation)
    #     asset_doc = get_current_project_asset(fields=["data.fps"])
    #     destination_path = container["namespace"]

    #     task = unreal.AssetImportTask()
    #     task.options = unreal.FbxImportUI()

    #     task.set_editor_property('filename', source_path)
    #     task.set_editor_property('destination_path', destination_path)
    #     # strip suffix
    #     task.set_editor_property('destination_name', name)
    #     task.set_editor_property('replace_existing', True)
    #     task.set_editor_property('automated', True)
    #     task.set_editor_property('save', True)

    #     # set import options here
    #     task.options.set_editor_property(
    #         'automated_import_should_detect_type', False)
    #     task.options.set_editor_property(
    #         'original_import_type', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    #     task.options.set_editor_property(
    #         'mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
    #     task.options.set_editor_property('import_mesh', False)
    #     task.options.set_editor_property('import_animations', True)
    #     task.options.set_editor_property('override_full_name', True)

    #     task.options.anim_sequence_import_data.set_editor_property(
    #         'animation_length',
    #         unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME
    #     )
    #     task.options.anim_sequence_import_data.set_editor_property(
    #         'import_meshes_in_bone_hierarchy', False)
    #     task.options.anim_sequence_import_data.set_editor_property(
    #         'use_default_sample_rate', False)
    #     task.options.anim_sequence_import_data.set_editor_property(
    #         'custom_sample_rate', asset_doc.get("data", {}).get("fps"))
    #     task.options.anim_sequence_import_data.set_editor_property(
    #         'import_custom_attribute', True)
    #     task.options.anim_sequence_import_data.set_editor_property(
    #         'import_bone_tracks', True)
    #     task.options.anim_sequence_import_data.set_editor_property(
    #         'remove_redundant_keys', False)
    #     task.options.anim_sequence_import_data.set_editor_property(
    #         'convert_scene', True)

    #     skeletal_mesh = EditorAssetLibrary.load_asset(
    #         container.get('namespace') + "/" + container.get('asset_name'))
    #     skeleton = skeletal_mesh.get_editor_property('skeleton')
    #     task.options.set_editor_property('skeleton', skeleton)

    #     # do import fbx and replace existing data
    #     unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    #     container_path = f'{container["namespace"]}/{container["objectName"]}'
    #     # update metadata
    #     up.imprint(
    #         container_path,
    #         {
    #             "representation": str(representation["_id"]),
    #             "parent": str(representation["parent"])
    #         })

    #     asset_content = EditorAssetLibrary.list_assets(
    #         destination_path, recursive=True, include_folder=True
    #     )

    #     for a in asset_content:
    #         EditorAssetLibrary.save_asset(a)

    # def remove(self, container):
    #     path = container["namespace"]
    #     parent_path = os.path.dirname(path)

    #     EditorAssetLibrary.delete_directory(path)

    #     asset_content = EditorAssetLibrary.list_assets(
    #         parent_path, recursive=False, include_folder=True
    #     )

    #     if len(asset_content) == 0:
    #         EditorAssetLibrary.delete_directory(parent_path)
