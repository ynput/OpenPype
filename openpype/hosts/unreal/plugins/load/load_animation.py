# -*- coding: utf-8 -*-
"""Load FBX with animations."""
import json

from openpype.pipeline.context_tools import get_current_project_asset
from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api.plugin import UnrealBaseLoader
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    containerise,
)


class AnimationFBXLoader(UnrealBaseLoader):
    """Load Unreal SkeletalMesh from FBX."""

    families = ["animation"]
    label = "Import FBX Animation"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    @staticmethod
    def _import_fbx_task(
        filename, destination_path, destination_name, replace, automated,
        skeleton
    ):
        asset_doc = get_current_project_asset(fields=["data.fps"])
        fps = asset_doc.get("data", {}).get("fps")

        options_properties = [
            ["automated_import_should_detect_type", "False"],
            ["original_import_type",
             "unreal.FBXImportType.FBXIT_SKELETAL_MESH"],
            ["mesh_type_to_import",
             "unreal.FBXImportType.FBXIT_ANIMATION"],
            ["import_mesh", "False"],
            ["import_animations", "True"],
            ["override_full_name", "True"],
            ["skeleton", f"get_asset({skeleton})"]
        ]

        sub_options_properties = [
            ["anim_sequence_import_data", "animation_length",
             "unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME"],
            ["anim_sequence_import_data",
             "import_meshes_in_bone_hierarchy", "False"],
            ["anim_sequence_import_data", "use_default_sample_rate", "False"],
            ["anim_sequence_import_data", "custom_sample_rate", str(fps)],
            ["anim_sequence_import_data", "import_custom_attribute", "True"],
            ["anim_sequence_import_data", "import_bone_tracks", "True"],
            ["anim_sequence_import_data", "remove_redundant_keys", "False"],
            ["anim_sequence_import_data", "convert_scene", "True"]
        ]

        params = {
            "filename": filename,
            "destination_path": destination_path,
            "destination_name": destination_name,
            "replace_existing": replace,
            "automated": automated,
            "save": True,
            "options_properties": options_properties,
            "sub_options_properties": sub_options_properties
        }

        send_request("import_fbx_task", params=params)

    def _process(self, asset_dir, asset_name, instance_name):
        automated = False
        actor = None
        skeleton = None

        if instance_name:
            automated = True
            actor, skeleton = send_request(
                "get_actor_and_skeleton",
                params={"instance_name": instance_name})

        if not actor:
            return None

        self._import_fbx_task(
            self.fname, asset_dir, asset_name, False, automated,
            skeleton)

        asset_content = send_request(
            "list_assets", params={
                "directory_path": asset_dir,
                "recursive": True,
                "include_folder": True})

        animation = None

        if animations := send_request(
            "get_assets_of_class",
            params={"asset_list": asset_content, "class_name": "AnimSequence"},
        ):
            animation = animations[0]

        if animation:
            send_request(
                "apply_animation_to_actor",
                params={
                    "actor_path": actor,
                    "animation_path": animation})

        return animation

    def load(self, context, name=None, namespace=None, options=None):
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
            options (dict): Those would be data to be imprinted. This is not
                            used now, data are imprinted by `containerise()`.
        """
        # Create directory for asset and OpenPype container
        hierarchy = context.get('asset').get('data').get('parents')
        root = self.root
        asset = context.get('asset').get('name')
        asset_name = f"{asset}_{name}" if asset else f"{name}"

        asset_dir, container_name = send_request(
            "create_unique_asset_name", params={
                "root": root,
                "asset": asset,
                "name": name})

        master_level = send_request(
            "get_first_asset_of_class",
            params={
                "class_name": "World",
                "path": f"{root}/{hierarchy[0]}",
                "recursive": False})

        hierarchy_dir = root
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
        hierarchy_dir = f"{hierarchy_dir}/{asset}"

        level = send_request(
            "get_first_asset_of_class",
            params={
                "class_name": "World",
                "path": f"{hierarchy_dir}/",
                "recursive": False})

        send_request("save_all_dirty_levels")
        send_request("load_level", params={"level_path": level})

        send_request("make_directory", params={"directory_path": asset_dir})

        libpath = self.fname.replace("fbx", "json")

        with open(libpath, "r") as fp:
            data = json.load(fp)

        instance_name = data.get("instance_name")

        animation = self._process(asset_dir, asset_name, instance_name)

        asset_content = send_request(
            "list_assets", params={
                "directory_path": hierarchy_dir,
                "recursive": True,
                "include_folder": False})

        # Get the sequence for the layout, excluding the camera one.
        all_sequences = send_request(
            "get_assets_of_class",
            params={
                "asset_list": asset_content,
                "class_name": "LevelSequence"})
        sequences = [
            a for a in all_sequences
            if "_camera" not in a.split("/")[-1]]

        send_request(
            "apply_animation",
            params={
                "animation_path": animation,
                "instance_name": instance_name,
                "sequences": sequences})

        data = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": self.__class__.__name__,
            "representation": str(context["representation"]["_id"]),
            "parent": str(context["representation"]["parent"]),
            "family": context["representation"]["context"]["family"]
        }

        containerise(asset_dir, container_name, data)

        send_request("save_current_level")
        send_request("load_level", params={"level_path": master_level})

        return send_request(
            "list_assets", params={
                "directory_path": asset_dir,
                "recursive": True,
                "include_folder": True})

    def update(self, container, representation):
        filename = get_representation_path(representation)
        asset_dir = container["namespace"]
        asset_name = container["asset_name"]

        skeleton = send_request(
            "get_skeleton_from_skeletal_mesh",
            params={
                "skeletal_mesh_path": f"{asset_dir}/{asset_name}"})

        self._import_fbx_task(
            filename, asset_dir, asset_name, True, True, skeleton)

        super(UnrealBaseLoader, self).update(container, representation)
