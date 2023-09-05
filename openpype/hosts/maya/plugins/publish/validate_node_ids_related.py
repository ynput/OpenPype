import pyblish.api

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib
from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidatePipelineOrder,
)


class ValidateNodeIDsRelated(pyblish.api.InstancePlugin,
                             OptionalPyblishPluginMixin):
    """Validate nodes have a related Colorbleed Id to the instance.data[asset]

    """

    order = ValidatePipelineOrder
    label = 'Node Ids Related (ID)'
    hosts = ['maya']
    families = ["model",
                "look",
                "rig"]
    optional = True

    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               openpype.hosts.maya.api.action.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        """Process all nodes in instance (including hierarchy)"""
        if not self.is_active(instance.data):
            return

        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                ("Nodes IDs found that are not related to asset "
                 "'{}' : {}").format(instance.data['asset'], invalid))

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""
        invalid = list()

        asset_id = str(instance.data['assetEntity']["_id"])

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
