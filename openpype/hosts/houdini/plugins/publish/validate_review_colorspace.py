# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.pipeline.publish import RepairAction
from openpype.hosts.houdini.api.action import SelectROPAction
from openpype.hosts.houdini.api.colorspace import get_default_display_view_colorspace  # noqa

import os
import hou


class SetDefaultViewSpaceAction(RepairAction):
    label = "Set default view colorspace"
    icon = "mdi.monitor"


class ValidateReviewColorspace(pyblish.api.InstancePlugin,
                               OptionalPyblishPluginMixin):
    """Validate Review Colorspace parameters.

    It checks if 'OCIO Colorspace' parameter was set to valid value.
    """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["review"]
    hosts = ["houdini"]
    label = "Validate Review Colorspace"
    actions = [SetDefaultViewSpaceAction, SelectROPAction]

    optional = True

    def process(self, instance):

        if not self.is_active(instance.data):
            return

        if os.getenv("OCIO") is None:
            self.log.debug(
                "Default Houdini colorspace is used, "
                " skipping check.."
            )
            return

        rop_node = hou.node(instance.data["instance_node"])
        if rop_node.evalParm("colorcorrect") != 2:
            # any colorspace settings other than default requires
            # 'Color Correct' parm to be set to 'OpenColorIO'
            raise PublishValidationError(
                "'Color Correction' parm on '{}' ROP must be set to"
                " 'OpenColorIO'".format(rop_node.path())
            )

        if rop_node.evalParm("ociocolorspace") not in \
                hou.Color.ocio_spaces():

            raise PublishValidationError(
                "Invalid value: Colorspace name doesn't exist.\n"
                "Check 'OCIO Colorspace' parameter on '{}' ROP"
                .format(rop_node.path())
            )

    @classmethod
    def repair(cls, instance):
        """Set Default View Space Action.

        It is a helper action more than a repair action,
        used to set colorspace on opengl node to the default view.
        """

        rop_node = hou.node(instance.data["instance_node"])

        if rop_node.evalParm("colorcorrect") != 2:
            rop_node.setParms({"colorcorrect": 2})
            cls.log.debug(
                "'Color Correction' parm on '{}' has been set to"
                " 'OpenColorIO'".format(rop_node.path())
            )

        # Get default view colorspace name
        default_view_space = get_default_display_view_colorspace()

        rop_node.setParms({"ociocolorspace": default_view_space})
        cls.log.debug(
            "'OCIO Colorspace' parm on '{}' has been set to "
            "the default view color space '{}'"
            .format(rop_node, default_view_space)

        )
