from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateRigInputMeshes(pyblish.api.Validator):
    """Validate if all pgYetiMaya nodes have at least one input shape"""

    order = colorbleed.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["colorbleed.yetiRig"]
    label = "Yeti Rig Input Shapes"
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Yeti Rig has invalid input meshes")

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        # Get yeti nodes
        yeti_nodes = cmds.listRelatives(instance,
                                        type="pgYetiMaya",
                                        allDescendents=True,
                                        fullPath=True)
        # Get input meshes per node
        for node in yeti_nodes:
            attribute = "%s.inputGeometry" % node
            input_meshes = cmds.listConnections(attribute, source=True)
            if not input_meshes:
                cls.log.error("'%s' has no input meshes" % node)
                invalid.append(node)

        return []
