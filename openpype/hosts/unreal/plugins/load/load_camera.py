# -*- coding: utf-8 -*-
"""Load camera from FBX."""
from pathlib import Path

from openpype.client import get_assets, get_asset_by_name
from openpype.pipeline import (
    AVALON_CONTAINER_ID,
    legacy_io,
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as up


class CameraLoader(plugin.Loader):
    """Load Unreal StaticMesh from FBX"""

    families = ["camera"]
    label = "Load Camera"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

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

        return min_frame, max_frame, asset_data.get('data').get("fps")

    def load(self, context, name, namespace, options):
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
        hierarchy_dir = root
        hierarchy_dir_list = []
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
            hierarchy_dir_list.append(hierarchy_dir)
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)

        # Create a unique name for the camera directory
        unique_number = 1
        if up.send_request_literal("does_directory_exist",
                                   params=[f"{hierarchy_dir}/{asset}"]):
            asset_content = up.send_request_literal(
                "list_assets", params=[f"{root}/{asset}", "False", "True"])

            # Get highest number to make a unique name
            folders = [a for a in asset_content
                       if a[-1] == "/" and f"{name}_" in a]
            f_numbers = []
            for f in folders:
                # Get number from folder name. Splits the string by "_" and
                # removes the last element (which is a "/").
                f_numbers.append(int(f.split("_")[-1][:-1]))
            f_numbers.sort()
            if not f_numbers:
                unique_number = 1
            else:
                unique_number = f_numbers[-1] + 1

        asset_dir, container_name = up.send_request_literal(
            "create_unique_asset_name", params=[
                hierarchy_dir, asset, name, unique_number])

        asset_path = Path(asset_dir)
        asset_path_parent = str(asset_path.parent.as_posix())

        container_name += suffix

        up.send_request("make_directory", params=[asset_dir])

        # Create map for the shot, and create hierarchy of map. If the maps
        # already exist, we will use them.
        h_dir = hierarchy_dir_list[0]
        h_asset = hierarchy[0]
        master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"
        if not up.send_request_literal(
                "does_asset_exist", params=[master_level]):
            up.send_request(
                "new_level", params=[f"{h_dir}/{h_asset}_map"])

        level = f"{asset_path_parent}/{asset}_map.{asset}_map"
        if not up.send_request_literal(
                "does_asset_exist", params=[level]):
            up.send_request(
                "new_level", params=[f"{asset_path_parent}/{asset}_map"])

            up.send_request("load_level", params=[master_level])
            up.send_request("add_level_to_world", params=[level])
        up.send_request("save_all_dirty_levels")
        up.send_request("load_level", params=[level])

        # TODO refactor
        #   - Creationg of hierarchy should be a function in unreal integration
        #       - it's used in multiple loaders but must not be loader's logic
        #       - hard to say what is purpose of the loop
        #   - variables does not match their meaning
        #       - why scene is stored to sequences?
        #       - asset documents vs. elements
        #   - cleanup variable names in whole function
        #       - e.g. 'asset', 'asset_name', 'asset_data', 'asset_doc'
        #   - really inefficient queries of asset documents
        #   - existing asset in scene is considered as "with correct values"
        #   - variable 'elements' is modified during it's loop
        # Get all the sequences in the hierarchy. It will create them, if
        # they don't exist.
        sequences = []
        frame_ranges = []
        for (h_dir, h) in zip(hierarchy_dir_list, hierarchy):
            root_content = up.send_request_literal(
                "list_assets", params=[h_dir, "False", "False"])

            print(root_content)

            existing_sequences = up.send_request_literal(
                "get_assets_of_class",
                params=[root_content, "LevelSequence"])

            print(existing_sequences)

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
                    frame_ranges.append(
                        up.send_request_literal(
                            "get_sequence_frame_range",
                            params=[sequence]))

        project_name = legacy_io.active_project()
        data = get_asset_by_name(project_name, asset)["data"]
        start_frame = 0
        end_frame = data.get('clipOut') - data.get('clipIn') + 1
        fps = data.get("fps")

        cam_sequence = up.send_request(
            "generate_sequence",
            params=[
                f"{asset}_camera", asset_dir, start_frame, end_frame, fps])

        # Add sequences data to hierarchy
        for i in range(0, len(sequences) - 1):
            up.send_request(
                "set_sequence_hierarchy",
                params=[
                    sequences[i], sequences[i + 1],
                    frame_ranges[i + 1][0], frame_ranges[i + 1][1]])

        up.send_request(
            "set_sequence_hierarchy",
            params=[
                sequences[-1], cam_sequence,
                data.get('clipIn'), data.get('clipOut')])

        up.send_request(
            "import_camera",
            params=[
                cam_sequence, self.fname])

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

        up.send_request("save_all_dirty_levels")
        up.send_request("load_level", params=[master_level])

        asset_content = up.send_request_literal(
            "list_assets", params=[asset_dir, "True", "True"])

        up.send_request(
            "save_listed_assets", params=[str(asset_content)])

        return asset_content

    def update(self, container, representation):
        asset_dir = container.get("namespace")
        context = representation.get("context")
        asset = container.get('asset')

        root = "/Game/OpenPype"
        hierarchy = context.get('hierarchy').split("/")
        h_dir = f"{root}/{hierarchy[0]}"
        h_asset = hierarchy[0]
        master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"

        parent_sequence = up.send_request(
            "remove_camera", params=[root, asset_dir])

        project_name = legacy_io.active_project()
        data = get_asset_by_name(project_name, asset)["data"]
        start_frame = 0
        end_frame = data.get('clipOut') - data.get('clipIn') + 1
        fps = data.get("fps")

        cam_sequence = up.send_request(
            "generate_sequence",
            params=[
                f"{asset}_camera", asset_dir, start_frame, end_frame, fps])

        up.send_request(
            "set_sequence_hierarchy",
            params=[
                parent_sequence, cam_sequence,
                data.get('clipIn'), data.get('clipOut')])

        up.send_request(
            "import_camera",
            params=[
                cam_sequence, str(representation["data"]["path"])])

        data = {
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"])
        }
        up.send_request(
            "imprint", params=[f"{asset_dir}/{container.get('container_name')}", str(data)])

        up.send_request("save_all_dirty_levels")
        up.send_request("load_level", params=[master_level])

        asset_content = up.send_request_literal(
            "list_assets", params=[asset_dir, "True", "True"])

        up.send_request(
            "save_listed_assets", params=[str(asset_content)])

    def remove(self, container):
        root = "/Game/OpenPype"

        up.send_request(
            "remove_camera", params=[root, container.get("namespace")])

        up.send_request(
            "remove_asset", params=[container.get("namespace")])
