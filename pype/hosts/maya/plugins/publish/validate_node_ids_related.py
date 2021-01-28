import pyblish.api
import pype.api

from avalon import io
import pype.hosts.maya.action

from pype.hosts.maya import lib


class ValidateNodeIDsRelated(pyblish.api.InstancePlugin):
    """Validate nodes have a related Colorbleed Id to the instance.data[asset]

    """

    order = pype.api.ValidatePipelineOrder
    label = 'Node Ids Related (ID)'
    hosts = ['maya']
    families = ["model",
                "look",
                "rig"]
    optional = True

    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.hosts.maya.action.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all nodes in instance (including hierarchy)"""
        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes IDs found that are not related to asset "
                               "'{}' : {}".format(instance.data['asset'],
                                                  invalid))

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""
        invalid = list()

        asset = instance.data['asset']
        asset_data = io.find_one(
            {
                "name": asset,
                "type": "asset"
            },
            projection={"_id": True}
        )
        asset_id = str(asset_data['_id'])

        # We do want to check the referenced nodes as we it might be
        # part of the end product
        for node in instance:

            _id = lib.get_id(node)
            if not _id:
                continue

            node_asset_id = _id.split(":", 1)[0]
            if node_asset_id != asset_id:
                invalid.append(node)

        return invalid
