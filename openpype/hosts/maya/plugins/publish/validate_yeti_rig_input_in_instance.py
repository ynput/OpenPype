from maya import cmds

import pyblish.api

import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateYetiRigInputShapesInInstance(pyblish.api.Validator,
                                           OptionalPyblishPluginMixin):
    """Validate if all input nodes are part of the instance's hierarchy"""

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["yetiRig"]
    label = "Yeti Rig Input Shapes In Instance"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("Yeti Rig has invalid input meshes")

    @classmethod
    def get_invalid(cls, instance):

        input_set = next((i for i in instance if i == "input_SET"), None)
        assert input_set, "Current %s instance has no `input_SET`" % instance

        # Get all children, we do not care about intermediates
        input_nodes = cmds.ls(cmds.sets(input_set, query=True), long=True)
        dag = cmds.ls(input_nodes, dag=True, long=True)
        shapes = cmds.ls(dag, long=True, shapes=True, noIntermediate=True)

        # Allow publish without input meshes.
        if not shapes:
            cls.log.debug("Found no input meshes for %s, skipping ..."
                          % instance)
            return []

        # check if input node is part of groomRig instance
        instance_lookup = set(instance[:])
        invalid = [s for s in shapes if s not in instance_lookup]

        return invalid
