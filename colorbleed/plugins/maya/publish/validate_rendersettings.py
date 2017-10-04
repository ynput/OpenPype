import maya.cmds as cmds

import pyblish.api
import colorbleed.api


class ValidateResources(pyblish.api.InstancePlugin):
    """Validates the globar render settings

    * File Name Prefix must be as followed:
        * vray: renders/<Scene>/<Layer>/<Layer>
        * arnold: renders/<Scene>/<RenderLayer>/<RenderLayer>
        * default: renders/<Scene>/<RenderLayer>/<RenderLayer>

    * Frame Padding must be:
        * default: 4
    """

    order = colorbleed.api.ValidateContentsOrder
    label = "Render Settings"
    hosts = ["maya"]
    families = ["colorbleed.renderlayer"]

    def process(self, instance):

        renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")

        default_padding = 4
        default_prefix = {
            "vray": "<Scene>/<Scene>_<Layer>/<Layer>",
            "arnold": "<Scene>/<Scene>_<RenderLayer>/<RenderLayer>"
        }

        if renderer == "vray":
            prefix = cmds.getAttr("vraySettings.fileNamePrefix")
            padding = cmds.getAttr("vraySettings.fileNamePadding")
        else:
            prefix = cmds.getAttr("defaultRenderGlobals.fileNamePrefix")
            padding = cmds.getAttr("defaultRenderGlobals.fileNamePadding")

        filename_prefix = default_prefix[renderer]
        assert padding == default_padding, AttributeError(
            "Expecting padding of 4 ( 0000 )"
        )
        assert prefix == filename_prefix, AttributeError(
            "Wrong file name prefix, expecting %s" % filename_prefix
        )
