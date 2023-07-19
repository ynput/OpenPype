# -*- coding: utf-8 -*-
"""Load camera from FBX."""
from pathlib import Path

from openpype.client import get_assets, get_asset_by_name
from openpype.pipeline import (
    AYON_CONTAINER_ID,
    get_current_project_name,
)
from openpype.hosts.unreal.api.plugin import UnrealBaseLoader
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    containerise,
)


class CameraLoader(UnrealBaseLoader):
    """Load Unreal StaticMesh from FBX"""

    families = ["camera"]
    label = "Load Camera"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    @staticmethod
    def _create_levels(
        hierarchy_dir_list, hierarchy, asset_dir, asset
    ):
        # Create map for the shot, and create hierarchy of map. If the maps
        # already exist, we will use them.
        h_dir = hierarchy_dir_list[0]
        h_asset = hierarchy[0]
        master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"
        if not send_request(
                "does_asset_exist", params={"asset_path": master_level}):
            send_request(
                "new_level",
                params={"level_path": f"{h_dir}/{h_asset}_map"})

        level = f"{asset_dir}/{asset}_map_camera.{asset}_map_camera"
        if not send_request(
                "does_asset_exist", params={"asset_path": level}):
            send_request(
                "new_level",
                params={"level_path": f"{asset_dir}/{asset}_map_camera"})

            send_request("load_level", params={"level_path": master_level})
            send_request("add_level_to_world", params={"level_path": level})

        send_request("save_all_dirty_levels")
        send_request("load_level", params={"level_path": level})

        return master_level, level

    @staticmethod
    def _get_frame_info(h_dir):
        project_name = get_current_project_name()
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

    def _get_sequences(self, hierarchy_dir_list, hierarchy):
        frame_ranges = []
        sequences = []
        for (h_dir, h) in zip(hierarchy_dir_list, hierarchy):
            root_content = send_request(
                "list_assets", params={
                    "directory_path": h_dir,
                    "recursive": False,
                    "include_folder": False})

            if existing_sequences := send_request(
                "get_assets_of_class",
                params={
                    "asset_list": root_content, "class_name": "LevelSequence"},
            ):
                for sequence in existing_sequences:
                    sequences.append(sequence)
                    frame_ranges.append(
                        send_request(
                            "get_sequence_frame_range",
                            params={"sequence_path": sequence}))
            else:
                start_frame, end_frame, fps = self._get_frame_info(h_dir)
                sequence = send_request(
                    "generate_sequence",
                    params={
                        "asset_name": h,
                        "asset_path": h_dir,
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                        "fps": fps})

                sequences.append(sequence)
                frame_ranges.append((start_frame, end_frame))

        return sequences, frame_ranges

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

        hierarchy_dir = root
        hierarchy_dir_list = []
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
            hierarchy_dir_list.append(hierarchy_dir)

        # Create a unique name for the camera directory
        unique_number = 1
        if send_request(
                "does_directory_exist",
                params={"directory_path": f"{hierarchy_dir}/{asset}"}):
            asset_content = send_request(
                "list_assets", params={
                    "directory_path": f"{root}/{asset}",
                    "recursive": False,
                    "include_folder": True})

            # Get highest number to make a unique name
            folders = [a for a in asset_content
                       if a[-1] == "/" and f"{name}_" in a]
            f_numbers = [int(f.split("_")[-1][:-1]) for f in folders]
            f_numbers.sort()
            unique_number = f_numbers[-1] + 1 if f_numbers else 1

        asset_dir, container_name = send_request(
            "create_unique_asset_name", params={
                "root": hierarchy_dir,
                "asset": asset,
                "name": name,
                "version": unique_number})

        send_request("make_directory", params={"directory_path": asset_dir})

        master_level, level = self._create_levels(
            hierarchy_dir_list, hierarchy, asset_dir, asset)

        sequences, frame_ranges = self._get_sequences(
            hierarchy_dir_list, hierarchy)

        project_name = get_current_project_name()
        data = get_asset_by_name(project_name, asset)["data"]

        cam_sequence = send_request(
            "generate_camera_sequence",
            params={
                "asset": asset,
                "asset_dir": asset_dir,
                "sequences": sequences,
                "frame_ranges": frame_ranges,
                "level": level,
                "fps": data.get("fps"),
                "clip_in": data.get("clipIn"),
                "clip_out": data.get("clipOut")})

        send_request(
            "import_camera",
            params={
                "sequence_path": cam_sequence,
                "import_filename": self.filepath_from_context(context)})

        send_request(
            "set_sequences_range",
            params={
                "sequence": cam_sequence,
                "clip_in": data.get("clipIn"),
                "clip_out": data.get("clipOut"),
                "frame_start": data.get("frameStart")})

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": str(context["representation"]["_id"]),
            "parent": str(context["representation"]["parent"]),
            "family": context["representation"]["context"]["family"]
        }

        containerise(asset_dir, container_name, data)

        send_request("save_all_dirty_levels")
        send_request("load_level", params={"level_path": master_level})

        assets = send_request(
            "list_assets", params={
                "directory_path": hierarchy_dir_list[0],
                "recursive": True,
                "include_folder": False})

        send_request("save_listed_assets", params={"asset_list": assets})

        return assets

    def update(self, container, representation):
        sequence_path, curr_time, is_cam_lock, vp_loc, vp_rot = send_request(
            "get_current_sequence_and_level_info")

        self.log.info(f"curr_time: {curr_time}")

        new_sequence = send_request(
            "update_camera",
            params={
                "asset_dir": container.get('namespace'),
                "asset": container.get('asset'),
                "root": self.root})

        send_request(
            "import_camera",
            params={
                "sequence_path": new_sequence,
                "import_filename": str(representation["data"]["path"])})

        project_name = get_current_project_name()
        asset = container.get('asset')
        data = get_asset_by_name(project_name, asset)["data"]

        send_request(
            "set_sequences_range",
            params={
                "sequence": new_sequence,
                "clip_in": data.get("clipIn"),
                "clip_out": data.get("clipOut"),
                "frame_start": data.get("frameStart")})

        super(CameraLoader, self).update(container, representation)

        send_request("save_all_dirty_levels")

        namespace = container.get('namespace').replace(f"{self.root}/", "")
        ms_asset = namespace.split('/')[0]
        asset_path = f"{self.root}/{ms_asset}"

        assets = send_request(
            "list_assets", params={
                "directory_path": asset_path,
                "recursive": True,
                "include_folder": False})

        send_request("save_listed_assets", params={"asset_list": assets})

        send_request(
            "get_and_load_master_level", params={"path": asset_path})

        send_request(
            "set_current_sequence_and_level_info",
            params={
                "sequence_path": sequence_path,
                "curr_time": curr_time,
                "is_cam_lock": is_cam_lock,
                "vp_loc": vp_loc,
                "vp_rot": vp_rot})

    def remove(self, container):
        root = self.root
        path = container["namespace"]
        asset = container.get('asset')

        send_request(
            "remove_camera", params={
                "asset_dir": path, "asset": asset, "root": root})

        super(CameraLoader, self).remove(container)
