"""
Requires:
    context     -> anatomyData
    context     -> projectEntity
    context     -> assetEntity
    instance    -> asset
    instance    -> subset
    instance    -> family

Optional:
    instance    -> version
    instance    -> resolutionWidth
    instance    -> resolutionHeight
    instance    -> fps

Provides:
    instance    -> projectEntity
    instance    -> assetEntity
    instance    -> anatomyData
    instance    -> version
    instance    -> latestVersion
"""

import copy
import json

from avalon import io
import pyblish.api


class CollectAnatomyInstanceData(pyblish.api.InstancePlugin):
    """Collect Instance specific Anatomy data."""

    order = pyblish.api.CollectorOrder + 0.49
    label = "Collect Anatomy Instance data"

    def process(self, instance):
        # get all the stuff from the database
        anatomy_data = copy.deepcopy(instance.context.data["anatomyData"])
        project_entity = instance.context.data["projectEntity"]
        context_asset_entity = instance.context.data["assetEntity"]

        asset_name = instance.data["asset"]
        # Check if asset name is the same as what is in context
        # - they may be different, e.g. in NukeStudio
        if context_asset_entity["name"] == asset_name:
            asset_entity = context_asset_entity

        else:
            asset_entity = io.find_one({
                "type": "asset",
                "name": asset_name,
                "parent": project_entity["_id"]
            })

        subset_name = instance.data["subset"]
        version_number = instance.data.get("version")
        latest_version = None

        if asset_entity:
            subset_entity = io.find_one({
                "type": "subset",
                "name": subset_name,
                "parent": asset_entity["_id"]
            })

            if subset_entity is None:
                self.log.debug("Subset entity does not exist yet.")
            else:
                version_entity = io.find_one(
                    {
                        "type": "version",
                        "parent": subset_entity["_id"]
                    },
                    sort=[("name", -1)]
                )
                if version_entity:
                    latest_version = version_entity["name"]

        # If version is not specified for instance or context
        if version_number is None:
            # TODO we should be able to change default version by studio
            # preferences (like start with version number `0`)
            version_number = 1
            # use latest version (+1) if already any exist
            if latest_version is not None:
                version_number += int(latest_version)

        anatomy_updates = {
            "asset": asset_name,
            "family": instance.data["family"],
            "subset": subset_name,
            "version": version_number
        }

        task_name = instance.data.get("task")
        if task_name:
            anatomy_updates["task"] = task_name

        # Version should not be collected since may be instance
        anatomy_data.update(anatomy_updates)

        resolution_width = instance.data.get("resolutionWidth")
        if resolution_width:
            anatomy_data["resolution_width"] = resolution_width

        resolution_height = instance.data.get("resolutionHeight")
        if resolution_height:
            anatomy_data["resolution_height"] = resolution_height

        pixel_aspect = instance.data.get("pixelAspect")
        if pixel_aspect:
            anatomy_data["pixel_aspect"] = float("{:0.2f}".format(
                float(pixel_aspect)))

        fps = instance.data.get("fps")
        if fps:
            anatomy_data["fps"] = float("{:0.2f}".format(
                float(fps)))

        instance.data["projectEntity"] = project_entity
        instance.data["assetEntity"] = asset_entity
        instance.data["anatomyData"] = anatomy_data
        instance.data["latestVersion"] = latest_version
        # TODO should be version number set here?
        instance.data["version"] = version_number

        self.log.info("Instance anatomy Data collected")
        self.log.debug(json.dumps(anatomy_data, indent=4))
