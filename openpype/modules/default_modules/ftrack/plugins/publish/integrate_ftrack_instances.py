import os
import json
import copy
import pyblish.api


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

        # Create review components
        # Change asset name of each new component for review
        first_review_repre = True
        for repre in review_representations:
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

            # Create copy of base comp item and append it
            component_item = copy.deepcopy(base_component_item)
            # Change location
            component_item["component_path"] = repre["published_path"]
            # Change component data
            component_item["component_data"] = {
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
            if first_review_repre:
                first_review_repre = False
            else:
                # Add representation name to asset name of "not first" review
                component_item["asset_data"]["name"] += repre["name"].title()

            # Create copy of item before setting location
            src_components_to_add.append(
                (repre, copy.deepcopy(component_item))
            )
            # Set location
            component_item["component_location"] = ftrack_server_location
            # Add item to component list
            component_list.append(component_item)

        # Create thumbnail components
        # TODO what if there is multiple thumbnails?
        for repre in thumbnail_representations:
            if not repre.get("published_path"):
                comp_files = repre["files"]
                if isinstance(comp_files, (tuple, list, set)):
                    filename = comp_files[0]
                else:
                    filename = comp_files

                repre["published_path"] = os.path.join(
                    repre["stagingDir"], filename
                )

            component_item["component_path"] = repre["published_path"]
            component_item["component_data"] = {
                "name": "thumbnail"
            }
            component_item["thumbnail"] = True
            # Create copy of item before setting location
            src_components_to_add.append(
                (repre, copy.deepcopy(component_item))
            )
            # Set location
            component_item["component_location"] = ftrack_server_location
            # Add item to component list
            component_list.append(component_item)

        # Add source components for review and thubmnail components
        for repre, component_item in src_components_to_add:
            # Make sure thumbnail is disabled
            component_item["thumbnail"] = False
            # Set location
            component_item["component_location"] = unmanaged_location
            # Modify name of component to have suffix "_src"
            component_data = component_item["component_data"]
            component_name = component_data["name"]
            component_data["name"] = component_name + "_src"
            component_list.append(component_item)

        # Add others representations as component
        for repre in other_representations:
            # Create copy of base comp item and append it
            component_item = copy.deepcopy(base_component_item)
            component_item["component_data"] = {
                "name": repre["name"]
            }
            component_item["component_location"] = unmanaged_location
            component_list.append(component_item)

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
