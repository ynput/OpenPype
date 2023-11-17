# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.pipeline.publish import RepairAction
from openpype.hosts.houdini.api.action import SelectROPAction
from openpype.hosts.houdini.api.lib import (
    get_houdini_color_settings,
    set_review_color_space
)

import os
import hou


class SetReviewColorSpaceAction(RepairAction):
    label = "Set Default Review Color Space"
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
    actions = [SetReviewColorSpaceAction, SelectROPAction]

    optional = True

    def process(self, instance):

        if not self.is_active(instance.data):
            return

        if os.getenv("OCIO") is None:
            self.log.debug(
                "Using Houdini's Default Color Management, "
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

        color_settings = get_houdini_color_settings()
        # skip if houdini color settings are disabled
        if color_settings["enabled"]:
            review_color_space = color_settings["review_color_space"]
            # skip if review color space setting is empty.
            if review_color_space and \
                    rop_node.evalParm("ociocolorspace") != review_color_space:

                raise PublishValidationError(
                    "Invalid value: Colorspace name doesn't match studio "
                    "settings.\nCheck 'OCIO Colorspace' parameter on '{}' ROP"
                    .format(rop_node.path())
                )

    @classmethod
    def repair(cls, instance):
        """Set Default Review Space Action.

        It sets ociocolorspace parameter.

        If workfile settings are enabled, it will use the value
        exposed in the settings.

        If the value exposed in the settings is empty,
        it will use the default colorspace corresponding to
        the display & view of the current Houdini session.
        """

        opengl_node = hou.node(instance.data["instance_node"])
        set_review_color_space(opengl_node, log=cls.log)
