# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.pipeline.publish import RepairAction
from openpype.hosts.houdini.api.action import SelectROPAction


class SetDefaultViewSpaceAction(RepairAction):
    label = "Set default view space"
    icon = "mdi.monitor"


class ValidateReviewColorspace(pyblish.api.InstancePlugin):
    """Validate Review Colorspace parameters.

    It checks if 'OCIO Colorspace' parameter was set to valid value.
    """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["review"]
    hosts = ["houdini"]
    label = "Validate Review Colorspace"
    actions = [SetDefaultViewSpaceAction, SelectROPAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                ("'OCIO Colorspace' parameter is not valid."),
                title=self.label
            )

    @classmethod
    def get_invalid(cls, instance):
        import hou  # noqa
        import os

        rop_node = hou.node(instance.data["instance_node"])
        if os.getenv("OCIO") is None:
            cls.log.warning(
                "Default Houdini colorspace is used, "
                " skipping check.."
            )
            return

        if rop_node.evalParm("colorcorrect") != 2:
            # any colorspace settings other than default requires
            # 'Color Correct' parm to be set to 'OpenColorIO'
            rop_node.setParms({"colorcorrect": 2})
            cls.log.debug(
                "'Color Correct' parm on '%s' has been set to"
                " 'OpenColorIO'", rop_node
            )

        if rop_node.evalParm("ociocolorspace") not in \
                hou.Color.ocio_spaces():

            cls.log.error(
                "'OCIO Colorspace' value on '%s' is not valid, "
                "select a valid option from the dropdown menu.",
                rop_node
            )
            return rop_node

    @classmethod
    def repair(cls, instance):
        """Set Default View Space Action.

        It is a helper action more than a repair action,
        used to set colorspace on opengl node to the default view.
        """

        import hou
        from openpype.pipeline.colorspace import get_display_view_colorspace_name #noqa
        from openpype.hosts.houdini.api.lib import get_color_management_preferences #noqa

        rop_node = hou.node(instance.data["instance_node"])

        data =  get_color_management_preferences()
        config_path = data.get("config")
        display =  data.get("display")
        view =  data.get("view")

        cls.log.debug("Get default view colorspace name..")

        default_view_space = get_display_view_colorspace_name(config_path,
                                                              display, view)

        rop_node.setParms({"ociocolorspace": default_view_space})
        cls.log.debug(
            "'OCIO Colorspace' parm on '%s' has been set to "
            "the default view color space '%s'",
            default_view_space, rop_node
        )
