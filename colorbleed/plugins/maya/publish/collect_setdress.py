from collections import defaultdict
import pyblish.api

from maya import cmds, mel
from avalon import maya as amaya
from colorbleed.maya import lib

import pprint


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
            transforms = lib.get_container_transforms(container, members)
            root = lib.get_container_transforms(container, transforms,
                                                root=True)
            if root not in instance_lookup:
                continue

            # retrieve all matrix data
            matrix_data = self.get_matrix_data(sorted(transforms))

            # Gather info for new data entry
            reference_node = cmds.ls(members, type="reference")[0]
            namespace = cmds.referenceQuery(reference_node, namespace=True)
            representation_id = container["representation"]
            data[representation_id].append({
                 "loader": container["loader"],
                 "matrix": matrix_data,
                 "namespace": namespace
            })

        instance.data["scenedata"] = dict(data)

    def get_file_rule(self, rule):
        return mel.eval('workspace -query -fileRuleEntry "{}"'.format(rule))

    def get_matrix_data(self, members):

        matrix_data = {}
        for idx, member in enumerate(members):
            matrix = cmds.xform(member, query=True, matrix=True)
            if matrix == lib.DEFAULT_MATRIX:
                continue
            matrix_data[idx] = matrix

        return matrix_data
