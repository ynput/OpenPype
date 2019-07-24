import pyblish.api
from avalon import io


@pyblish.api.log
class ValidateScript(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["workfile"]
    label = "Check script settings"
    hosts = ["nuke"]

    def process(self, instance):
        ctx_data = instance.context.data
        asset_name = ctx_data["asset"]

        asset = io.find_one({
            "type": "asset",
            "name": asset_name
        })
        asset_data = asset["data"]

        # These attributes will be checked
        attributes = [
            "fps", "fstart", "fend",
            "resolution_width", "resolution_height", "handle_start", "handle_end"
        ]

        # Value of these attributes can be found on parents
        hierarchical_attributes = ["fps", "resolution_width", "resolution_height", "pixel_aspect", "handle_start", "handle_end"]

        missing_attributes = []
        asset_attributes = {}
        for attr in attributes:
            if attr in asset_data:
                asset_attributes[attr] = asset_data[attr]

            elif attr in hierarchical_attributes:
                # Try to find fps on parent
                parent = asset['parent']
                if asset_data['visualParent'] is not None:
                    parent = asset_data['visualParent']

                value = self.check_parent_hierarchical(parent, attr)
                if value is None:
                    missing_attributes.append(attr)
                else:
                    asset_attributes[attr] = value
            else:
                missing_attributes.append(attr)

        # Raise error if attributes weren't found on asset in database
        if len(missing_attributes) > 0:
            atr = ", ".join(missing_attributes)
            msg = 'Missing attributes "{}" in asset "{}"'
            message = msg.format(atr, asset_name)
            raise ValueError(message)

        # Get handles from database, Default is 0 (if not found)
        handle_start = 0
        handle_end = 0
        if "handle_start" in asset_attributes:
            handle_start = asset_attributes["handle_start"]
        if "handle_end" in asset_attributes:
            handle_end = asset_attributes["handle_end"]

        # Set frame range with handles
        # asset_attributes["fstart"] -= handle_start
        # asset_attributes["fend"] += handle_end

        # Get values from nukescript
        script_attributes = {
            "handle_start": ctx_data["handle_start"],
            "handle_end": ctx_data["handle_end"],
            "fps": ctx_data["fps"],
            "fstart": ctx_data["startFrame"],
            "fend": ctx_data["endFrame"],
            "resolution_width": ctx_data["resolution_width"],
            "resolution_height": ctx_data["resolution_height"],
            "pixel_aspect": ctx_data["pixel_aspect"]
        }

        # Compare asset's values Nukescript X Database
        not_matching = []
        for attr in attributes:
            self.log.debug("asset vs script attribute: {0}, {1}".format(
                asset_attributes[attr], script_attributes[attr]))
            if asset_attributes[attr] != script_attributes[attr]:
                not_matching.append(attr)

        # Raise error if not matching
        if len(not_matching) > 0:
            msg = "Attributes '{}' are not set correctly"
            # Alert user that handles are set if Frame start/end not match
            if (
                (("fstart" in not_matching) or ("fend" in not_matching)) and
                ((handle_start > 0) or (handle_end > 0))
            ):
                msg += " (`handle_start` are set to {})".format(handle_start)
                msg += " (`handle_end` are set to {})".format(handle_end)
            message = msg.format(", ".join(not_matching))
            raise ValueError(message)

    def check_parent_hierarchical(self, entityId, attr):
        if entityId is None:
            return None
        entity = io.find_one({"_id": entityId})
        if attr in entity['data']:
            self.log.info(attr)
            return entity['data'][attr]
        else:
            return self.check_parent_hierarchical(entity['parent'], attr)
