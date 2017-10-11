from collections import defaultdict
import pyblish.api

from maya import cmds, mel
from avalon import maya as amaya
from colorbleed.maya import lib


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
        data = defaultdict(list)

        for container in containers:
            members = cmds.sets(container["objectName"], query=True)
            transforms = lib.get_container_transfroms(container, members)
            root = lib.get_container_transfroms(container, members, root=True)
            if root not in instance_lookup:
                continue

            representation_id = container["representation"]
            shapes = [m for m in members if
                      cmds.objectType(m, isAType="shape") is True]

            look_ids = [self.get_look_id(shape) for shape in shapes]

            # Support for re-opened setdress scenes where the only connected
            # transform node is the root node. This is due to how references
            # are loaded in combination with the containers.

            matrix_data = self.get_matrix_data(transforms)

            # Gather info for new data entry
            reference_node = cmds.ls(members, type="reference")[0]
            namespace = cmds.referenceQuery(reference_node, namespace=True)
            data[representation_id].append({
                 "loader": container["loader"],
                 "matrix": matrix_data,
                 "namespace": namespace,
                 "look_id": look_ids
            })

        instance.data["scenedata"] = dict(data)

    def get_file_rule(self, rule):
        return mel.eval('workspace -query -fileRuleEntry "{}"'.format(rule))

    def get_matrix_data(self, members):

        matrix_data = []
        for member in members:
            self.log.info(member)
            matrix = cmds.xform(member, query=True, matrix=True)
            matrix_data.append(matrix)

        return matrix_data

    def get_look_id(self, node):
        """Get the look id of the assigned shader"""
        shad_engine = cmds.listConnections(node, type="shadingEngine")
        if not shad_engine or shad_engine == "initialShadingEngine":
            return

        return cmds.getAttr("{}.cbId".format(shad_engine[0])).split(":")[0]
