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
