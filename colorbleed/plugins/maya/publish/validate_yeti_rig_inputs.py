from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateYetiRigInputShapesRequired(pyblish.api.Validator):
    """Validate if all input nodes have at least one outgoing connection.

    The input nodes are the approach to ensure the rig can be hooked up to
    other meshes, for example: Alembic Mesh.
    """

    order = colorbleed.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["colorbleed.yetiRig"]
    label = "Yeti Rig Input Shapes Required"
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Yeti Rig has invalid input meshes")

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        input_set = [i for i in instance if i == "input_SET"]
        assert input_set, "Current %s instance has no `input_SET`" % instance

        # Get all children
        input_nodes = cmds.ls(cmds.sets(input_set, query=True), long=True)
        children = [i for i in cmds.listRelatives(input_nodes,
                                                  allDescendents=True,
                                                  fullPath=True)]
        children = cmds.ls(children,
                           type="shape",
                           long=True,
                           noIntermediate=True)

        for shape in children:
            incoming = cmds.listConnections(shape,
                                            source=False,
                                            destination=True,
                                            connections=True)
            if not incoming:
                cls.log.error("%s has not incoming connections" % shape)
                invalid.append(shape)

        return invalid
