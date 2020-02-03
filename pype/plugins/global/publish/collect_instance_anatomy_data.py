"""
Requires:
    context     -> anatomyData
    context     -> projectEntity
    context     -> assetEntity
    instance    -> asset
    instance    -> subset
    instance    -> family

Optional:
    instance    -> resolutionWidth
    instance    -> resolutionHeight
    instance    -> fps

Provides:
    instance    -> anatomyData
"""

import copy
import json

from avalon import io
import pyblish.api


class CollectInstanceAnatomyData(pyblish.api.InstancePlugin):
    """Fill templates with data needed for publish"""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect instance anatomy data"
    hosts = ["maya", "nuke", "standalonepublisher"]

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

        instance.context.data["assetEntity"] = asset_entity
        instance.context.data["projectEntity"] = project_entity

        subset_name = instance.data["subset"]
        subset_entity = io.find_one({
            "type": "subset",
            "name": subset_name,
            "parent": asset_entity["_id"]
        })

        version_number = instance.data.get("version")
        if version_number is None:
            version_number = instance.context.data.get("version")

        latest_version = None
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

        if version_number is None:
            # TODO we should be able to change this version by studio
            # preferences (like start with version number `0`)
            version_number = 1
            if latest_version is not None:
                version_number += int(latest_version)

        # Version should not be collected since may be instance
        anatomy_data.update({
            "asset": asset_entity["name"],
            "family": instance.data["family"],
            "subset": subset_name,
            "version": version_number
        })

        resolution_width = instance.data.get("resolutionWidth")
        if resolution_width:
            anatomy_data["resolution_width"] = resolution_width

        resolution_height = instance.data.get("resolutionHeight")
        if resolution_height:
            anatomy_data["resolution_height"] = resolution_height

        fps = instance.data.get("fps")
        if resolution_height:
            anatomy_data["fps"] = fps

        instance.data["anatomyData"] = anatomy_data
        instance.data["latestVersion"] = latest_version
        # TODO check if template is used anywhere
        # instance.data["template"] = template

        # TODO we should move this to any Validator
        # # We take the parent folder of representation 'filepath'
        # instance.data["assumedDestination"] = os.path.dirname(
        #     (anatomy.format(template_data))["publish"]["path"]
        # )

        self.log.info("Instance anatomy Data collected")
        self.log.debug(json.dumps(anatomy_data, indent=4))
