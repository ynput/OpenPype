from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


def pairs(iterable):
    """Iterate over iterable per group of two"""
    a = iter(iterable)
    for i, y in zip(a, a):
        yield i, y


def get_invalid_sets(shape):
    """Get sets that are considered related but do not contain the shape.

    In some scenarios Maya keeps connections to multiple shaders
    even if just a single one is assigned on the full object.

    These are related sets returned by `maya.cmds.listSets` that don't
    actually have the shape as member.

    """

    invalid = []
    sets = cmds.listSets(object=shape, t=1, extendToShape=False) or []
    for s in sets:
        members = cmds.sets(s, query=True, nodesOnly=True)
        if not members:
            invalid.append(s)
            continue

        members = set(cmds.ls(members, long=True))
        if shape not in members:
            invalid.append(s)

    return invalid


def disconnect(node_a, node_b):
    """Remove all connections between node a and b."""

    # Disconnect outputs
    outputs = cmds.listConnections(node_a,
                                   plugs=True,
                                   connections=True,
                                   source=False,
                                   destination=True)
    for output, destination in pairs(outputs):
        if destination.split(".", 1)[0] == node_b:
            cmds.disconnectAttr(output, destination)

    # Disconnect inputs
    inputs = cmds.listConnections(node_a,
                                  plugs=True,
                                  connections=True,
                                  source=True,
                                  destination=False)
    for input, source in pairs(inputs):
        if source.split(".", 1)[0] == node_b:
            cmds.disconnectAttr(source, input)


class ValidateMeshShaderConnections(pyblish.api.InstancePlugin):
    """Ensure mesh shading engine connections are valid.

    In some scenarios Maya keeps connections to multiple shaders even if just
    a single one is assigned on the shape.

    These are related sets returned by `maya.cmds.listSets` that don't
    actually have the shape as member.

    """

    order = pype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    label = "Mesh Shader Connections"
    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.api.RepairAction]

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Shapes found with invalid shader "
                               "connections: {0}".format(invalid))

    @staticmethod
    def get_invalid(instance):

        shapes = cmds.ls(instance[:], dag=1, leaf=1, shapes=1, long=True)

        # todo: allow to check anything that can have a shader
        shapes = cmds.ls(shapes, noIntermediate=True, long=True, type="mesh")

        invalid = []
        for shape in shapes:
            if get_invalid_sets(shape):
                invalid.append(shape)

        return invalid

    @classmethod
    def repair(cls, instance):

        shapes = cls.get_invalid(instance)
        for shape in shapes:
            invalid_sets = get_invalid_sets(shape)
            for set_node in invalid_sets:
                disconnect(shape, set_node)
