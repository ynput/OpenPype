from maya import cmds

import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    RepairAction,
    PublishValidationError,
    OptionalPyblishPluginMixin
)

from openpype.hosts.maya.api import lib
import openpype.hosts.maya.api.action


class ValidateRigControllersArnoldAttributes(pyblish.api.InstancePlugin,
                                             OptionalPyblishPluginMixin):
    """Validate rig control curves have no keyable arnold attributes.

    The Arnold plug-in will create curve attributes like:
        - aiRenderCurve
        - aiCurveWidth
        - aiSampleRate
        - aiCurveShaderR
        - aiCurveShaderG
        - aiCurveShaderB

    Unfortunately these attributes visible in the channelBox are *keyable*
    by default and visible in the channelBox. As such pressing a regular "S"
    set key shortcut will set keys on these attributes too, thus cluttering
    the animator's scene.

    This validator will ensure they are hidden or unkeyable attributes.

    """
    order = ValidateContentsOrder + 0.05
    label = "Rig Controllers (Arnold Attributes)"
    hosts = ["maya"]
    families = ["rig"]
    optional = False
    actions = [RepairAction,
               openpype.hosts.maya.api.action.SelectInvalidAction]

    attributes = [
        "rcurve",
        "cwdth",
        "srate",
        "ai_curve_shaderr",
        "ai_curve_shaderg",
        "ai_curve_shaderb"
    ]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError('{} failed, see log '
                               'information'.format(self.label))

    @classmethod
    def get_invalid(cls, instance):

        controls_set = instance.data["rig_sets"].get("controls_SET")
        if not controls_set:
            return []

        controls = cmds.sets(controls_set, query=True) or []
        if not controls:
            return []

        shapes = cmds.ls(controls,
                         dag=True,
                         leaf=True,
                         long=True,
                         shapes=True,
                         noIntermediate=True)
        curves = cmds.ls(shapes, type="nurbsCurve", long=True)

        invalid = list()
        for node in curves:

            for attribute in cls.attributes:
                if cmds.attributeQuery(attribute, node=node, exists=True):
                    plug = "{}.{}".format(node, attribute)
                    if cmds.getAttr(plug, keyable=True):
                        invalid.append(node)
                        break

        return invalid

    @classmethod
    def repair(cls, instance):

        invalid = cls.get_invalid(instance)
        with lib.undo_chunk():
            for node in invalid:
                for attribute in cls.attributes:
                    if cmds.attributeQuery(attribute, node=node, exists=True):
                        plug = "{}.{}".format(node, attribute)
                        cmds.setAttr(plug, channelBox=False, keyable=False)
