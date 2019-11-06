import os

from maya import cmds, mel
import pymel.core as pm

import pyblish.api
import pype.api
import pype.maya.lib as lib


class ValidateRenderSettings(pyblish.api.InstancePlugin):
    """Validates the global render settings

    * File Name Prefix must be as followed:
        * vray: maya/<Scene>/<Layer>/<Layer>
        * default: maya/<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>

    * Frame Padding must be:
        * default: 4

    * Animation must be toggle on, in Render Settings - Common tab:
        * vray: Animation on standard of specific
        * arnold: Frame / Animation ext: Any choice without "(Single Frame)"
        * redshift: Animation toggled on

    NOTE:
        The repair function of this plugin does not repair the animation
        setting of the render settings due to multiple possibilities.

    """

    order = pype.api.ValidateContentsOrder
    label = "Render Settings"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [pype.api.RepairAction]

    DEFAULT_PADDING = 4
    RENDERER_PREFIX = {"vray": "maya/<scene>/<Layer>/<Layer>"}
    DEFAULT_PREFIX = "maya/<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Invalid render settings found for '%s'!"
                             % instance.name)

    @classmethod
    def get_invalid(cls, instance):

        invalid = False

        renderer = instance.data['renderer']
        layer = instance.data['setMembers']

        # Get the node attributes for current renderer
        attrs = lib.RENDER_ATTRS.get(renderer, lib.RENDER_ATTRS['default'])
        prefix = lib.get_attr_in_layer("{node}.{prefix}".format(**attrs),
                                       layer=layer)
        padding = lib.get_attr_in_layer("{node}.{padding}".format(**attrs),
                                        layer=layer)

        anim_override = lib.get_attr_in_layer("defaultRenderGlobals.animation",
                                              layer=layer)
        if not anim_override:
            invalid = True
            cls.log.error("Animation needs to be enabled. Use the same "
                          "frame for start and end to render single frame")

        fname_prefix = cls.get_prefix(renderer)

        if prefix != fname_prefix:
            invalid = True
            cls.log.error("Wrong file name prefix: %s (expected: %s)"
                          % (prefix, fname_prefix))

        if padding != cls.DEFAULT_PADDING:
            invalid = True
            cls.log.error("Expecting padding of {} ( {} )".format(
                cls.DEFAULT_PADDING, "0" * cls.DEFAULT_PADDING))

        return invalid

    @classmethod
    def get_prefix(cls, renderer):
        prefix = cls.RENDERER_PREFIX.get(renderer, cls.DEFAULT_PREFIX)
        # maya.cmds and pymel.core return only default project directory and
        # not the current one but only default.
        output_path = os.path.join(
            mel.eval("workspace -q -rd;"), pm.workspace.fileRules["images"]
        )
        # Workfile paths can be configured to have host name in file path.
        # In this case we want to avoid duplicate folder names.
        if "maya" in output_path.lower():
            prefix = prefix.replace("maya/", "")

        return prefix

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

            fname_prefix = cls.get_prefix(renderer)
            cmds.setAttr("{}.{}".format(node, prefix_attr),
                         fname_prefix, type="string")

            # Repair padding
            padding_attr = render_attrs["padding"]
            cmds.setAttr("{}.{}".format(node, padding_attr),
                         cls.DEFAULT_PADDING)
