from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    ValidateMeshOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


def _as_report_list(values, prefix="- ", suffix="\n"):
    """Return list as bullet point list for a report"""
    if not values:
        return ""
    return prefix + (suffix + prefix).join(values)


class ValidateMeshNoNegativeScale(pyblish.api.Validator,
                                  OptionalPyblishPluginMixin):
    """Ensure that meshes don't have a negative scale.

    Using negatively scaled proxies in a VRayMesh results in inverted
    normals. As such we want to avoid this.

    We also avoid this on the rig or model because these are often the
    previous steps for those that are cached to proxies so we can catch this
    issue early.

    """

    order = ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    label = 'Mesh No Negative Scale'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = False

    @staticmethod
    def get_invalid(instance):
        meshes = cmds.ls(instance,
                         type='mesh',
                         long=True,
                         noIntermediate=True)

        invalid = []
        for mesh in meshes:
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            scale = cmds.getAttr("{0}.scale".format(transform))[0]

            if any(x < 0 for x in scale):
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Meshes found with negative scale:\n\n{0}".format(
                    _as_report_list(sorted(invalid))
                ),
                title="Negative scale"
            )
