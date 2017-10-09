from collections import defaultdict
import pyblish.api

from maya import cmds, mel
from avalon import maya as amaya


class CollectSetDress(pyblish.api.InstancePlugin):
    """Collect all relevant setdress items

    Collected data:

        * File name
        * Compatible loader
        * Matrix per instance
        * Namespace
    """

    order = pyblish.api.CollectorOrder + 0.49
    label = "Set Dress"
    families = ["colorbleed.setdress"]

    def process(self, instance):

        # Find containers
        containers = amaya.ls()

        # Get all content from the instance
        instance_lookup = set(cmds.ls(instance, type="transform", long=True))
        alembic_data = defaultdict(list)

        for container in containers:

            members = cmds.sets(container["objectName"], query=True)
            transforms = cmds.ls(members, type="transform", long=True)
            if not transforms:
                self.log.warning("Container is invalid, missing transform:"
                                 "%s", container["objectName"])
                continue
            if len(transforms) > 1:
                self.log.warning("Container is invalid, more than one "
                                 "transform: %s", container['objectName'])
                continue

            root = transforms[0]
            if root not in instance_lookup:
                continue

            representation_id = container["representation"]
            matrix = cmds.xform(root, query=True, matrix=True)

            # Gather info for new data entry
            reference_node = cmds.ls(members, type="reference")[0]
            namespace = cmds.referenceQuery(reference_node, namespace=True)
            alembic_data[representation_id].append({
                 "loader": container["loader"],
                 "matrix": matrix,
                 "namespace": namespace
            })

        instance.data["scenedata"] = dict(alembic_data)

    def get_file_rule(self, rule):
        return mel.eval('workspace -query -fileRuleEntry "{}"'.format(rule))
