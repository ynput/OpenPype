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
        topnode = cmds.sets(instance.name, query=True)[0]
        instance_lookup = set(cmds.ls(instance, type="transform", long=True))
        data = defaultdict(list)

        hierarchy_nodes = []
        for i, container in enumerate(containers):
            members = cmds.sets(container["objectName"], query=True)
            transforms = lib.get_container_transforms(container, members)
            root = lib.get_container_transforms(container,
                                                transforms,
                                                root=True)
            if root not in instance_lookup:
                continue

            # Retrieve all matrix data
            hierarchy = cmds.listRelatives(root, parent=True, fullPath=True)[0]
            relative_hierarchy = hierarchy.replace(topnode, "*")
            hierarchy_nodes.append(relative_hierarchy)

            # Gather info for new data entry
            reference_node = cmds.ls(members, type="reference")[0]
            namespace = cmds.referenceQuery(reference_node, namespace=True)
            representation_id = container["representation"]

            instance_data = {"loader": container["loader"],
                             "hierarchy": hierarchy,
                             "namespace": namespace.strip(":")}

            # Check if matrix differs from default and store changes
            matrix_data = self.get_matrix_data(root)
            if matrix_data:
                instance_data["matrix"] = matrix_data

            data[representation_id].append(instance_data)

        instance.data["scenedata"] = dict(data)
        instance.data["hierarchy"] = list(set(hierarchy_nodes))


    def get_file_rule(self, rule):
        return mel.eval('workspace -query -fileRuleEntry "{}"'.format(rule))

    def get_matrix_data(self, node):
        """Get the matrix of all members when they are not default

        Each matrix which differs from the default will be stored in a
        dictionary

        Args:
            members (list): list of transform nmodes
        Returns:
            dict
        """

        matrix = cmds.xform(node, query=True, matrix=True)
        if matrix == lib.DEFAULT_MATRIX:
            return

        return matrix
