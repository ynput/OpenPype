# -*- coding: utf-8 -*-
"""Loader for layouts."""
import json
import collections
from pathlib import Path

from openpype.client import get_asset_by_name, get_assets, get_representations
from openpype.pipeline import (
    discover_loader_plugins,
    loaders_from_representation,
    load_container,
    get_representation_path,
    AVALON_CONTAINER_ID,
    legacy_io,
)
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.settings import get_current_project_settings
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as up


class LayoutLoader(plugin.Loader):
    """Load Layout from a JSON file"""

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout"
    icon = "code-fork"
    color = "orange"
    ASSET_ROOT = "/Game/OpenPype"

    # def _get_asset_containers(self, path):
    #     ar = unreal.AssetRegistryHelpers.get_asset_registry()

    #     asset_content = EditorAssetLibrary.list_assets(
    #         path, recursive=True)

    #     asset_containers = []

    #     # Get all the asset containers
    #     for a in asset_content:
    #         obj = ar.get_asset_by_object_path(a)
    #         if obj.get_asset().get_class().get_name() == 'AssetContainer':
    #             asset_containers.append(obj)

    #     return asset_containers

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

    def _import_animation(
        self, asset_dir, path, instance_name, skeleton, actors_dict,
        animation_file, bindings_dict, sequence
    ):
        anim_file = Path(animation_file)
        anim_file_name = anim_file.with_suffix('')

        anim_path = f"{asset_dir}/animations/{anim_file_name}"

        asset_doc = get_current_project_asset()
        fps = asset_doc.get("data", {}).get("fps")

        task_properties = [
            ("filename", up.format_string(str(
                path.with_suffix(f".{animation_file}")))),
            ("destination_path", up.format_string(anim_path)),
            ("destination_name", up.format_string(
                f"{instance_name}_animation")),
            ("replace_existing", "False"),
            ("automated", "True"),
            ("save", "False")
        ]

        options_properties = [
            ("automated_import_should_detect_type", "False"),
            ("original_import_type",
                "unreal.FBXImportType.FBXIT_SKELETAL_MESH"),
            ("mesh_type_to_import",
                "unreal.FBXImportType.FBXIT_SKELETAL_MESH"),
            ("original_import_type", "unreal.FBXImportType.FBXIT_ANIMATION"),
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
            ("anim_sequence_import_data", "convert_scene", "False")
        ]

        up.send_request(
            "import_fbx_task",
            params=[
                str(task_properties),
                str(options_properties),
                str(options_extra_properties)
            ])

        asset_content = up.send_request_literal(
            "list_assets", params=[anim_path, "False", "False"])

        up.send_request(
            "save_listed_assets", params=[str(asset_content)])

        animation = None

        animations = up.send_request_literal(
            "get_assets_of_class",
            params=[asset_content, "AnimSequence"])
        if animations:
            animation = animations[0]

        if animation:
            actor = None
            if actors_dict.get(instance_name):
                actors = up.send_request_literal(
                    "get_assets_of_class",
                    params=[
                        actors_dict.get(instance_name), "SkeletalMeshActor"])
                assert len(actors) == 1, (
                    "There should be only one skeleton in the loaded assets.")
                actor = actors[0]

            up.send_request(
                "apply_animation_to_actor", params=[actor, animation])

            if sequence:
                # Add animation to the sequencer
                bindings = bindings_dict.get(instance_name)

                for binding in bindings:
                    up.send_request(
                        "add_animation_to_sequencer",
                        params=[sequence, binding, animation])

    def _get_frame_info(self, h_dir):
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

    def _get_repre_docs_by_version_id(self, data):
        version_ids = {
            element.get("version")
            for element in data
            if element.get("representation")
        }
        version_ids.discard(None)

        output = collections.defaultdict(list)
        if not version_ids:
            return output

        project_name = legacy_io.active_project()
        repre_docs = get_representations(
            project_name,
            representation_names=["fbx", "abc"],
            version_ids=version_ids,
            fields=["_id", "parent", "name"]
        )
        for repre_doc in repre_docs:
            version_id = str(repre_doc["parent"])
            output[version_id].append(repre_doc)
        return output

    def _process(self, lib_path, asset_dir, sequence, repr_loaded=None):
        with open(lib_path, "r") as fp:
            data = json.load(fp)

        all_loaders = discover_loader_plugins()

        if not repr_loaded:
            repr_loaded = []

        path = Path(lib_path)

        skeleton_dict = {}
        actors_dict = {}
        bindings_dict = {}

        loaded_assets = []

        repre_docs_by_version_id = self._get_repre_docs_by_version_id(data)
        for element in data:
            representation = None
            repr_format = None
            if element.get('representation'):
                repre_docs = repre_docs_by_version_id[element.get("version")]
                if not repre_docs:
                    self.log.error(
                        f"No valid representation found for version "
                        f"{element.get('version')}")
                    continue
                repre_doc = repre_docs[0]
                representation = str(repre_doc["_id"])
                repr_format = repre_doc["name"]

                representation = str(repr_data.get('_id'))
            # This is to keep compatibility with old versions of the
            # json format.
            elif element.get('reference_fbx'):
                representation = element.get('reference_fbx')
                repr_format = 'fbx'
            elif element.get('reference_abc'):
                representation = element.get('reference_abc')
                repr_format = 'abc'

            # If reference is None, this element is skipped, as it cannot be
            # imported in Unreal
            if not representation:
                continue

            instance_name = element.get('instance_name')

            skeleton = None

            if representation not in repr_loaded:
                repr_loaded.append(representation)

                family = element.get('family')
                loaders = loaders_from_representation(
                    all_loaders, representation)

                loader = None

                if repr_format == 'fbx':
                    loader = self._get_fbx_loader(loaders, family)
                elif repr_format == 'abc':
                    loader = self._get_abc_loader(loaders, family)

                if not loader:
                    self.log.error(
                        f"No valid loader found for {representation}")
                    continue

                options = {
                    # "asset_dir": asset_dir
                }

                assets = load_container(
                    loader,
                    representation,
                    namespace=instance_name,
                    options=options
                )

                container = None

                asset_containers = up.send_request_literal(
                    "get_assets_of_class",
                    params=[assets, "AssetContainer"])
                assert len(asset_containers) == 1, (
                    "There should be only one AssetContainer in "
                    "the loaded assets.")
                container = asset_containers[0]

                skeletons = up.send_request_literal(
                    "get_assets_of_class",
                    params=[assets, "Skeleton"])
                assert len(skeletons) <= 1, (
                    "There should be one skeleton at most in "
                    "the loaded assets.")
                if skeletons:
                    skeleton = skeletons[0]

                loaded_assets.append(container)

                instances = [
                    item for item in data
                    if ((item.get('version') and
                        item.get('version') == element.get('version')) or
                        item.get('reference_fbx') == representation or
                        item.get('reference_abc') == representation)]

                for instance in instances:
                    # transform = instance.get('transform')
                    transform = str(instance.get('transform_matrix'))
                    basis = str(instance.get('basis'))
                    instance_name = instance.get('instance_name')

                    actors = []

                    if family == 'model':
                        (actors, _) = up.send_request_literal(
                            "process_family", params=[
                                assets, 'StaticMesh', instance_name,
                                transform, basis, sequence])
                    elif family == 'rig':
                        (actors, bindings) = up.send_request_literal(
                            "process_family", params=[
                                assets, 'SkeletalMesh', instance_name,
                                transform, basis, sequence])

                        actors_dict[instance_name] = actors
                        bindings_dict[instance_name] = bindings

                if skeleton:
                    skeleton_dict[representation] = skeleton
            else:
                skeleton = skeleton_dict.get(representation)

            animation_file = element.get('animation')

            if animation_file and skeleton:
                self._import_animation(
                    asset_dir, path, instance_name, skeleton, actors_dict,
                    animation_file, bindings_dict, sequence)

        return loaded_assets

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
        data = get_current_project_settings()
        create_sequences = data["unreal"]["level_sequences_for_layouts"]

        # Create directory for asset and avalon container
        hierarchy = context.get('asset').get('data').get('parents')
        root = self.ASSET_ROOT
        hierarchy_dir = root
        hierarchy_dir_list = []
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
            hierarchy_dir_list.append(hierarchy_dir)
        asset = context.get('asset').get('name')
        suffix = "_CON"
        asset_name = f"{asset}_{name}" if asset else name

        asset_dir, container_name = up.send_request_literal(
            "create_unique_asset_name", params=[hierarchy_dir, asset, name])

        asset_path = Path(asset_dir)
        asset_path_parent = str(asset_path.parent.as_posix())

        container_name += suffix

        up.send_request("make_directory", params=[asset_dir])

        master_level = None
        shot = ""
        sequences = []

        level = f"{asset_path_parent}/{asset}_map.{asset}_map"
        if not up.send_request_literal(
                "does_asset_exist", params=[level]):
            up.send_request(
                "new_level", params=[f"{asset_path_parent}/{asset}_map"])

        if create_sequences:
            # Create map for the shot, and create hierarchy of map. If the
            # maps already exist, we will use them.
            if hierarchy:
                h_dir = hierarchy_dir_list[0]
                h_asset = hierarchy[0]
                master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"
                if not up.send_request_literal(
                        "does_asset_exist", params=[master_level]):
                    up.send_request(
                        "new_level", params=[f"{h_dir}/{h_asset}_map"])

            if master_level:
                up.send_request("load_level", params=[master_level])
                up.send_request("add_level_to_world", params=[level])
                up.send_request("save_all_dirty_levels")
                up.send_request("load_level", params=[level])

            # Get all the sequences in the hierarchy. It will create them, if
            # they don't exist.
            frame_ranges = []
            for (h_dir, h) in zip(hierarchy_dir_list, hierarchy):
                root_content = up.send_request_literal(
                    "list_assets", params=[h_dir, "False", "False"])

                existing_sequences = up.send_request_literal(
                    "get_assets_of_class",
                    params=[root_content, "LevelSequence"])

                if not existing_sequences:
                    start_frame, end_frame, fps = self._get_frame_info(h_dir)
                    sequence = up.send_request(
                        "generate_master_sequence",
                        params=[h, h_dir, start_frame, end_frame, fps])

                    sequences.append(sequence)
                    frame_ranges.append((start_frame, end_frame))
                else:
                    for sequence in existing_sequences:
                        sequences.append(sequence)
                        frame_range = up.send_request_literal(
                            "get_sequence_frame_range",
                            params=[sequence])
                        frame_ranges.append(frame_range)

            project_name = legacy_io.active_project()
            data = get_asset_by_name(project_name, asset)["data"]
            shot_start_frame = 0
            shot_end_frame = data.get('clipOut') - data.get('clipIn') + 1
            fps = data.get("fps")

            shot = up.send_request(
                "generate_sequence",
                params=[
                    asset, asset_dir, shot_start_frame, shot_end_frame, fps])

            # sequences and frame_ranges have the same length
            for i in range(0, len(sequences) - 1):
                up.send_request(
                    "set_sequence_hierarchy",
                    params=[
                        sequences[i], sequences[i + 1],
                        frame_ranges[i + 1][0], frame_ranges[i + 1][1]])
                up.send_request(
                    "set_sequence_visibility",
                    params=[
                        sequences[i], frame_ranges[i][1],
                        frame_ranges[i + 1][0], frame_ranges[i + 1][1],
                        str([level])])

            if sequences:
                up.send_request(
                    "set_sequence_hierarchy",
                    params=[
                        sequences[-1], shot,
                        data.get('clipIn'), data.get('clipOut')])
                up.send_request(
                    "set_sequence_visibility",
                    params=[
                        sequences[-1], frame_ranges[-1][1],
                        data.get('clipIn'), data.get('clipOut'),
                        str([level])])

            up.send_request("load_level", params=[level])

        loaded_assets = self._process(self.fname, asset_dir, shot)

        up.send_request("save_listed_assets", params=[str(sequences)])

        up.send_request("save_current_level")

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
            "family": context["representation"]["context"]["family"],
            "loaded_assets": loaded_assets
        }
        up.send_request(
            "imprint", params=[f"{asset_dir}/{container_name}", str(data)])

        asset_content = up.send_request_literal(
            "list_assets", params=[asset_dir, "True", "False"])

        up.send_request(
            "save_listed_assets", params=[str(asset_content)])

        if master_level:
            up.send_request("load_level", params=[master_level])

        return asset_content

    def update(self, container, representation):
        root = "/Game/OpenPype"
        asset_dir = container.get('namespace')
        context = representation.get("context")

        data = get_current_project_settings()
        create_sequences = data["unreal"]["level_sequences_for_layouts"]

        master_level = None
        prev_level = None
        layout_sequence = ""

        if create_sequences:
            hierarchy = context.get('hierarchy').split("/")
            h_dir = f"{root}/{hierarchy[0]}"
            h_asset = hierarchy[0]
            master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"

            parent_path = Path(asset_dir).parent.as_posix()

            layout_level = up.send_request(
                "get_first_asset_of_class",
                params=["World", parent_path, "False"])

            up.send_request("load_level", params=[layout_level])

            layout_sequence = up.send_request(
                "get_first_asset_of_class",
                params=["LevelSequence", asset_dir, "False"])

            up.send_request(
                "delete_all_bound_assets", params=[layout_sequence])

        if not master_level:
            prev_level = up.send_request("get_current_level")

        source_path = get_representation_path(representation)

        loaded_assets = self._process(source_path, asset_dir, layout_sequence)

        data = {
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"]),
            "loaded_assets": loaded_assets
        }
        up.send_request(
            "imprint", params=[
                f"{asset_dir}/{container.get('container_name')}", str(data)])

        up.send_request("save_current_level")

        asset_content = up.send_request_literal(
            "list_assets", params=[asset_dir, "True", "False"])

        up.send_request(
            "save_listed_assets", params=[str(asset_content)])

        if master_level:
            up.send_request("load_level", params=[master_level])
        elif prev_level:
            up.send_request("load_level", params=[prev_level])


    def remove(self, container):
        """
        Delete the layout. First, check if the assets loaded with the layout
        are used by other layouts. If not, delete the assets.
        """
        root = "/Game/OpenPype"
        asset = container.get('asset')
        asset_dir = container.get('namespace')
        asset_name = container.get('asset_name')
        loaded_assets = container.get('loaded_assets')

        data = get_current_project_settings()
        create_sequences = data["unreal"]["level_sequences_for_layouts"]

        up.send_request(
            "remove_layout",
            params=[
                root, asset, asset_dir, asset_name, loaded_assets,
                "True" if create_sequences else "False"])
