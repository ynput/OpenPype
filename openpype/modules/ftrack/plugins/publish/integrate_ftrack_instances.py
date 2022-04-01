import os
import json
import copy
import pyblish.api
from pprint import pformat

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

    def process(self, instance):
        self.log.debug("instance {}".format(instance))

        instance_version = instance.data.get("version")
        if instance_version is None:
            raise ValueError("Instance version not set")

        version_number = int(instance_version)

        family = instance.data["family"]
        family_low = instance.data["family"].lower()

        asset_type = instance.data.get("ftrackFamily")
        if not asset_type and family_low in self.family_mapping:
            asset_type = self.family_mapping[family_low]

        self.log.debug(self.family_mapping)
        self.log.debug(family_low)

        # Ignore this instance if neither "ftrackFamily" or a family mapping is
        # found.
        if not asset_type:
            self.log.info((
                "Family \"{}\" does not match any asset type mapping"
            ).format(family))
            return

        instance_repres = instance.data.get("representations")
        if not instance_repres:
            self.log.info((
                "Skipping instance. Does not have any representations {}"
            ).format(str(instance)))
            return

        # Prepare FPS
        instance_fps = instance.data.get("fps")
        if instance_fps is None:
            instance_fps = instance.context.data["fps"]

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
                "comment": instance.context.data.get("comment") or ""
            },
            "component_overwrite": False,
            # This can be change optionally
            "thumbnail": False,
            # These must be changed for each component
            "component_data": None,
            "component_path": None,
            "component_location": None
        }

        ft_session = instance.context.data["ftrackSession"]

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
        unmanaged_location = ft_session.query(
            "Location where name is \"ftrack.unmanaged\""
        ).one()
        ftrack_server_location = ft_session.query(
            "Location where name is \"ftrack.server\""
        ).one()

        # Components data
        component_list = []
        # Components that will be duplicated to unmanaged location
        src_components_to_add = []

        # Create thumbnail components
        # TODO what if there is multiple thumbnails?
        first_thumbnail_component = None
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
                first_thumbnail_component = copy.deepcopy(thumbnail_item)
            # Set location
            thumbnail_item["component_location"] = ftrack_server_location
            # Add item to component list
            component_list.append(thumbnail_item)

        # Create review components
        # Change asset name of each new component for review
        is_first_review_repre = True
        not_first_components = []
        extended_asset_name = False
        for repre in review_representations:
            # Create copy of base comp item and append it
            review_item = copy.deepcopy(base_component_item)

            # condition for multiple reviewable representations
            # expand name to better label componenst
            if is_first_review_repre and len(review_representations) > 1:
                asset_name = review_item["asset_data"]["name"]
                # define new extended name
                extended_asset_name = "_".join(
                    (asset_name, repre["name"])
                )
                review_item["asset_data"]["name"] = extended_asset_name
                # and rename all already created components
                for _ci in component_list:
                    _ci["asset_data"]["name"] = extended_asset_name

                # and rename all already created src components
                for _sci in src_components_to_add:
                    _sci["asset_data"]["name"] = extended_asset_name

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

            # rename asset name only if multiple reviewable repre
            if is_first_review_repre:
                is_first_review_repre = False
            else:
                # Add representation name to asset name of "not first" review
                asset_name = review_item["asset_data"]["name"]
                review_item["asset_data"]["name"] = "_".join(
                    (asset_name, repre["name"])
                )
                not_first_components.append(review_item)

            # Create copy of item before setting location
            src_components_to_add.append(copy.deepcopy(review_item))

            # Set location
            review_item["component_location"] = ftrack_server_location
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
                new_thumbnail_component["component_location"] = (
                    ftrack_server_location
                )
                component_list.append(new_thumbnail_component)

        # Add source components for review and thubmnail components
        for copy_src_item in src_components_to_add:
            # Make sure thumbnail is disabled
            copy_src_item["thumbnail"] = False
            # Set location
            copy_src_item["component_location"] = unmanaged_location
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
            if extended_asset_name:
                other_item["asset_data"]["name"] = extended_asset_name

            other_item["component_data"] = {
                "name": repre["name"]
            }
            other_item["component_location"] = unmanaged_location
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
