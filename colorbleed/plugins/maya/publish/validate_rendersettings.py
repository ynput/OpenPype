import maya.cmds as cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateRenderSettings(pyblish.api.InstancePlugin):
    """Validates the global render settings

    * File Name Prefix must be as followed:
        * vray: <Scene>/<Layer>/<Layer>
        * arnold: <Scene>/<RenderLayer>/<RenderLayer>
        * default: <Scene>/<RenderLayer>/<RenderLayer>

    * Frame Padding must be:
        * default: 4

    NOTE:
        The repair function of this plugin will does not repair animation
        setting of the render settings due to multiple possibilities.

    """

    order = colorbleed.api.ValidateContentsOrder
    label = "Render Settings"
    hosts = ["maya"]
    families = ["colorbleed.renderlayer"]
    actions = [colorbleed.api.RepairAction]

    DEFAULT_PADDING = 4
    RENDERER_PREFIX = {"vray": "<Scene>/<Scene>_<Layer>/<Layer>"}
    DEFAULT_PREFIX = "<Scene>/<Scene>_<RenderLayer>/<RenderLayer>"

    def process(self, instance):

        renderer = instance.data['renderer']
        layer_node = instance.data['setMembers']

        # Main check animation
        animation = cmds.getAttr("defaultRenderGlobals.animation")
        assert animation is True, ("Animation needs to be enabled in the "
                                   "render settings")

        # Collect the filename prefix in the renderlayer
        with lib.renderlayer(layer_node):

            render_attrs = lib.RENDER_ATTRS.get(renderer,
                                                lib.RENDER_ATTRS['default'])
            node = render_attrs["node"]
            padding_attr = render_attrs["padding"]
            prefix_attr = render_attrs["prefix"]

            prefix = cmds.getAttr("{}.{}".format(node, prefix_attr))
            padding = cmds.getAttr("{}.{}".format(node, padding_attr))

            anim_override = cmds.getAttr("defaultRenderGlobals.animation")
            assert anim_override == animation, (
                "Animation neesd to be enabled. Use the same frame for start "
                "and end to render singel frame")

            fname_prefix = self.RENDERER_PREFIX.get(renderer,
                                                    self.DEFAULT_PREFIX)
            assert prefix == fname_prefix, (
                "Wrong file name prefix, expecting %s" % fname_prefix
            )
            assert padding == self.DEFAULT_PADDING, (
                "Expecting padding of {} ( {} )".format(
                    self.DEFAULT_PADDING, "0"*self.DEFAULT_PADDING)
            )

    @classmethod
    def repair(cls, instance):

        renderer = instance.data['renderer']
        layer_node = instance.data['setMembers']

        with lib.renderlayer(layer_node):
            default = lib.RENDER_ATTRS['default']
            render_attrs = lib.RENDER_ATTRS.get(renderer, default)

            # Repair prefix
            node = render_attrs["node"]
            prefix_attr = render_attrs["prefix"]

            fname_prefix = cls.RENDERER_PREFIX.get(renderer, cls.DEFAULT_PREFIX)
            cmds.setAttr("{}.{}".format(node, prefix_attr),
                         fname_prefix, type="string")

            # Repair padding
            padding_attr = render_attrs["padding"]
            cmds.setAttr("{}.{}".format(node, padding_attr),
                         cls.DEFAULT_PADDING)
