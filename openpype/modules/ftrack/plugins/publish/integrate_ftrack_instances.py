import os
import json
import copy
import pyblish.api

from openpype.lib import get_ffprobe_streams
from openpype.lib.profiles_filtering import filter_profiles


class IntegrateFtrackInstance(pyblish.api.InstancePlugin):
    """Collect ftrack component data (not integrate yet).

    Add ftrack component list to instance.
    """

    order = pyblish.api.IntegratorOrder + 0.48
    label = "Integrate Ftrack Component"
    families = ["ftrack"]

    family_mapping = {
        "camera": "cam",
        "look": "look",
        "mayaascii": "scene",
        "model": "geo",
        "rig": "rig",
        "setdress": "setdress",
        "pointcache": "cache",
        "render": "render",
        "prerender": "render",
        "render2d": "render",
        "nukescript": "comp",
        "write": "render",
        "review": "mov",
        "plate": "img",
        "audio": "audio",
        "workfile": "scene",
        "animation": "cache",
        "image": "img",
        "reference": "reference"
    }
    keep_first_subset_name_for_review = True
    asset_versions_status_profiles = {}

    def process(self, instance):
        self.log.debug("instance {}".format(instance))

        instance_repres = instance.data.get("representations")
        if not instance_repres:
            self.log.info((
                "Skipping instance. Does not have any representations {}"
            ).format(str(instance)))
            return

        instance_version = instance.data.get("version")
        if instance_version is None:
            raise ValueError("Instance version not set")

        version_number = int(instance_version)

        family = instance.data["family"]
        family_low = instance.data["family"].lower()

        asset_type = instance.data.get("ftrackFamily")
        if not asset_type and family_low in self.family_mapping:
            asset_type = self.family_mapping[family_low]

        if not asset_type:
            asset_type = "upload"

        self.log.debug(
            "Family: {}\nMapping: {}".format(family_low, self.family_mapping)
        )

        # Ignore this instance if neither "ftrackFamily" or a family mapping is
        # found.
        if not asset_type:
            self.log.info((
                "Family \"{}\" does not match any asset type mapping"
            ).format(family))
            return

        # Prepare FPS
        instance_fps = instance.data.get("fps")
        if instance_fps is None:
            instance_fps = instance.context.data["fps"]

        status_name = self._get_asset_version_status_name(instance)

        # Base of component item data
        # - create a copy of this object when want to use it
        base_component_item = {
            "assettype_data": {
                "short": asset_type,
            },
            "asset_data": {
                "name": instance.data["subset"],
            },
            "assetversion_data": {
                "version": version_number,
                "comment": instance.context.data.get("comment") or "",
                "status_name": status_name
            },
            "component_overwrite": False,
            # This can be change optionally
            "thumbnail": False,
            # These must be changed for each component
            "component_data": None,
            "component_path": None,
            "component_location": None,
            "component_location_name": None
        }

        # Filter types of representations
        review_representations = []
        thumbnail_representations = []
        other_representations = []
        for repre in instance_repres:
            self.log.debug("Representation {}".format(repre))
            repre_tags = repre.get("tags") or []
            if repre.get("thumbnail") or "thumbnail" in repre_tags:
                thumbnail_representations.append(repre)

            elif "ftrackreview" in repre_tags:
                review_representations.append(repre)

            else:
                other_representations.append(repre)

        # Prepare ftrack locations
        unmanaged_location_name = "ftrack.unmanaged"
        ftrack_server_location_name = "ftrack.server"

        # Components data
        component_list = []
        # Components that will be duplicated to unmanaged location
        src_components_to_add = []

        # Create thumbnail components
        # TODO what if there is multiple thumbnails?
        first_thumbnail_component = None
        first_thumbnail_component_repre = None
        for repre in thumbnail_representations:
            published_path = repre.get("published_path")
            if not published_path:
                comp_files = repre["files"]
                if isinstance(comp_files, (tuple, list, set)):
                    filename = comp_files[0]
                else:
                    filename = comp_files

                published_path = os.path.join(
                    repre["stagingDir"], filename
                )
                if not os.path.exists(published_path):
                    continue
                repre["published_path"] = published_path

            # Create copy of base comp item and append it
            thumbnail_item = copy.deepcopy(base_component_item)
            thumbnail_item["component_path"] = repre["published_path"]
            thumbnail_item["component_data"] = {
                "name": "thumbnail"
            }
            thumbnail_item["thumbnail"] = True
            # Create copy of item before setting location
            src_components_to_add.append(copy.deepcopy(thumbnail_item))
            # Create copy of first thumbnail
            if first_thumbnail_component is None:
                first_thumbnail_component_repre = repre
                first_thumbnail_component = thumbnail_item
            # Set location
            thumbnail_item["component_location_name"] = (
                ftrack_server_location_name
            )

            # Add item to component list
            component_list.append(thumbnail_item)

        if first_thumbnail_component is not None:
            width = first_thumbnail_component_repre.get("width")
            height = first_thumbnail_component_repre.get("height")
            if not width or not height:
                component_path = first_thumbnail_component["component_path"]
                streams = []
                try:
                    streams = get_ffprobe_streams(component_path)
                except Exception:
                    self.log.debug((
                        "Failed to retrieve information about intput {}"
                    ).format(component_path))

                for stream in streams:
                    if "width" in stream and "height" in stream:
                        width = stream["width"]
                        height = stream["height"]
                        break

            if width and height:
                component_data = first_thumbnail_component["component_data"]
                component_data["name"] = "ftrackreview-image"
                component_data["metadata"] = {
                    "ftr_meta": json.dumps({
                        "width": width,
                        "height": height,
                        "format": "image"
                    })
                }

        # Create review components
        # Change asset name of each new component for review
        is_first_review_repre = True
        not_first_components = []
        extended_asset_name = ""
        multiple_reviewable = len(review_representations) > 1
        for repre in review_representations:
            # Create copy of base comp item and append it
            review_item = copy.deepcopy(base_component_item)

            # get asset name and define extended name variant
            asset_name = review_item["asset_data"]["name"]
            extended_asset_name = "_".join(
                (asset_name, repre["name"])
            )

            # reset extended if no need for extended asset name
            if (
                self.keep_first_subset_name_for_review
                and is_first_review_repre
            ):
                extended_asset_name = ""
            else:
                # only rename if multiple reviewable
                if multiple_reviewable:
                    review_item["asset_data"]["name"] = extended_asset_name
                else:
                    extended_asset_name = ""

            # rename all already created components
            # only if first repre and extended name available
            if is_first_review_repre and extended_asset_name:
                # and rename all already created components
                for _ci in component_list:
                    _ci["asset_data"]["name"] = extended_asset_name

                # and rename all already created src components
                for _sci in src_components_to_add:
                    _sci["asset_data"]["name"] = extended_asset_name

                # rename also first thumbnail component if any
                if first_thumbnail_component is not None:
                    first_thumbnail_component[
                        "asset_data"]["name"] = extended_asset_name

            frame_start = repre.get("frameStartFtrack")
            frame_end = repre.get("frameEndFtrack")
            if frame_start is None or frame_end is None:
                frame_start = instance.data["frameStart"]
                frame_end = instance.data["frameEnd"]

            # Frame end of uploaded video file should be duration in frames
            # - frame start is always 0
            # - frame end is duration in frames
            duration = frame_end - frame_start + 1

            fps = repre.get("fps")
            if fps is None:
                fps = instance_fps

            # Change location
            review_item["component_path"] = repre["published_path"]
            # Change component data
            review_item["component_data"] = {
                # Default component name is "main".
                "name": "ftrackreview-mp4",
                "metadata": {
                    "ftr_meta": json.dumps({
                        "frameIn": 0,
                        "frameOut": int(duration),
                        "frameRate": float(fps)
                    })
                }
            }

            if is_first_review_repre:
                is_first_review_repre = False
            else:
                # later detection for thumbnail duplication
                not_first_components.append(review_item)

            # Create copy of item before setting location
            src_components_to_add.append(copy.deepcopy(review_item))

            # Set location
            review_item["component_location_name"] = (
                ftrack_server_location_name
            )
            # Add item to component list
            component_list.append(review_item)

        # Duplicate thumbnail component for all not first reviews
        if first_thumbnail_component is not None:
            for component_item in not_first_components:
                asset_name = component_item["asset_data"]["name"]
                new_thumbnail_component = copy.deepcopy(
                    first_thumbnail_component
                )
                new_thumbnail_component["asset_data"]["name"] = asset_name
                new_thumbnail_component["component_location_name"] = (
                    ftrack_server_location_name
                )
                component_list.append(new_thumbnail_component)

        # Add source components for review and thubmnail components
        for copy_src_item in src_components_to_add:
            # Make sure thumbnail is disabled
            copy_src_item["thumbnail"] = False
            # Set location
            copy_src_item["component_location_name"] = unmanaged_location_name
            # Modify name of component to have suffix "_src"
            component_data = copy_src_item["component_data"]
            component_name = component_data["name"]
            component_data["name"] = component_name + "_src"
            component_list.append(copy_src_item)

        # Add others representations as component
        for repre in other_representations:
            published_path = repre.get("published_path")
            if not published_path:
                continue
            # Create copy of base comp item and append it
            other_item = copy.deepcopy(base_component_item)

            # add extended name if any
            if (
                not self.keep_first_subset_name_for_review
                and extended_asset_name
            ):
                other_item["asset_data"]["name"] = extended_asset_name

            other_item["component_data"] = {
                "name": repre["name"]
            }
            other_item["component_location_name"] = unmanaged_location_name
            other_item["component_path"] = published_path
            component_list.append(other_item)

        def json_obj_parser(obj):
            return str(obj)

        self.log.debug("Components list: {}".format(
            json.dumps(
                component_list,
                sort_keys=True,
                indent=4,
                default=json_obj_parser
            )
        ))
        instance.data["ftrackComponentsList"] = component_list

    def _get_asset_version_status_name(self, instance):
        if not self.asset_versions_status_profiles:
            return None

        # Prepare filtering data for new asset version status
        anatomy_data = instance.data["anatomyData"]
        task_type = anatomy_data.get("task", {}).get("type")
        filtering_criteria = {
            "families": instance.data["family"],
            "hosts": instance.context.data["hostName"],
            "task_types": task_type
        }
        matching_profile = filter_profiles(
            self.asset_versions_status_profiles,
            filtering_criteria
        )
        if not matching_profile:
            return None

        return matching_profile["status"] or None
