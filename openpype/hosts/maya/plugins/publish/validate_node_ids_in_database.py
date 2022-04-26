import pyblish.api

import openpype.api
from openpype.pipeline import legacy_io
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib


class ValidateNodeIdsInDatabase(pyblish.api.InstancePlugin):
    """Validate if the CB Id is related to an asset in the database

    All nodes with the `cbId` attribute will be validated to ensure that
    the loaded asset in the scene is related to the current project.

    Tip: If there is an asset which is being reused from a different project
    please ensure the asset is republished in the new project

    """

    order = openpype.api.ValidatePipelineOrder
    label = 'Node Ids in Database'
    hosts = ['maya']
    families = ["*"]

    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               openpype.hosts.maya.api.action.GenerateUUIDsOnInvalidAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found asset IDs which are not related to "
                               "current project in instance: "
                               "`%s`" % instance.name)

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        # Get all id required nodes
        id_required_nodes = lib.get_id_required_nodes(referenced_nodes=True,
                                                      nodes=instance[:])

        # check ids against database ids
        db_asset_ids = legacy_io.find({"type": "asset"}).distinct("_id")
        db_asset_ids = set(str(i) for i in db_asset_ids)

        # Get all asset IDs
        for node in id_required_nodes:
            cb_id = lib.get_id(node)

            # Ignore nodes without id, those are validated elsewhere
            if not cb_id:
                continue

            asset_id = cb_id.split(":", 1)[0]
            if asset_id not in db_asset_ids:
                cls.log.error("`%s` has unassociated asset ID" % node)
                invalid.append(node)

        return invalid
