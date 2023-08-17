from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api.lib import pairwise
from openpype.pipeline.publish import (
    RepairAction,
    ValidateMeshOrder,
    PublishValidationError
)


def get_invalid_sets(shapes):
    """Return invalid sets for the given shapes.

    This takes a list of shape nodes to cache the set members for overlapping
    sets in the queries. This avoids many Maya set member queries.

    Returns:
        dict: Dictionary of shapes and their invalid sets, e.g.
            {"pCubeShape": ["set1", "set2"]}

    """

    cache = dict()
    invalid = dict()

    # Collect the sets from the shape
    for shape in shapes:
        invalid_sets = []
        sets = cmds.listSets(object=shape, t=1, extendToShape=False) or []
        for set_ in set(sets):

            members = cache.get(set_, None)
            if members is None:
                # Bugfix: When querying `maya.cmds.sets` with `nodesOnly=True`
                # instanced members will always return the first instance path
                # even though that might not be the actual member of the set
                # To resolve this we `maya.cmds.sets` regularly and filter to
                # objects using `maya.cmds.ls` with `objectsOnly`
                members = cmds.sets(set_, query=True)
                members = cmds.ls(members, objectsOnly=True, long=True)
                cache[set_] = set(members)

            # If the shape is not actually present as a member of the set
            # consider it invalid
            if shape not in members:
                invalid_sets.append(set_)

        if invalid_sets:
            invalid[shape] = invalid_sets

    return invalid


def disconnect(node_a, node_b):
    """Remove all connections between node a and b."""

    # Disconnect outputs
    outputs = cmds.listConnections(node_a,
                                   plugs=True,
                                   connections=True,
                                   source=False,
                                   destination=True)
    for output, destination in pairwise(outputs):
        if destination.split(".", 1)[0] == node_b:
            cmds.disconnectAttr(output, destination)

    # Disconnect inputs
    inputs = cmds.listConnections(node_a,
                                  plugs=True,
                                  connections=True,
                                  source=True,
                                  destination=False)
    for input, source in pairwise(inputs):
        if source.split(".", 1)[0] == node_b:
            cmds.disconnectAttr(source, input)


class ValidateMeshShaderConnections(pyblish.api.InstancePlugin):
    """Ensure mesh shading engine connections are valid.

    In some scenarios Maya keeps connections to multiple shaders even if just
    a single one is assigned on the shape.

    These are related sets returned by `maya.cmds.listSets` that don't
    actually have the shape as member.

    """

    order = ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    label = "Mesh Shader Connections"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               RepairAction]

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError("Shapes found with invalid shader "
                               "connections: {0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):

        nodes = instance[:]
        shapes = cmds.ls(nodes, noIntermediate=True, long=True, type="mesh")

        invalid_sets = get_invalid_sets(shapes)
        for node, sets in invalid_sets.items():
            cls.log.info("Node {} has invalid shader connection to: {}".format(
                node, sets
            ))

        return list(invalid_sets.keys())

    @classmethod
    def repair(cls, instance):

        shapes = cls.get_invalid(instance)
        invalid = get_invalid_sets(shapes)
        for shape, invalid_sets in invalid.items():
            for set_node in invalid_sets:
                disconnect(shape, set_node)
