import os
import re

from maya import cmds, mel
import pymel.core as pm

import pyblish.api
import pype.api
import pype.maya.lib as lib


class ValidateRenderSettings(pyblish.api.InstancePlugin):
    """Validates the global render settings

    * File Name Prefix must start with: `maya/<Scene>`
        all other token are customizable but sane values are:

        `maya/<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>`

        <Camera> token is supported also, usefull for multiple renderable
        cameras per render layer.

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

    ImagePrefixes = {
        'mentalray': 'defaultRenderGlobals.imageFilePrefix',
        'vray': 'vraySettings.fileNamePrefix',
        'arnold': 'defaultRenderGlobals.imageFilePrefix',
        'renderman': 'defaultRenderGlobals.imageFilePrefix',
        'redshift': 'defaultRenderGlobals.imageFilePrefix'
    }

    R_AOV_TOKEN = re.compile(
        r'%a|<aov>|<renderpass>', re.IGNORECASE)
    R_LAYER_TOKEN = re.compile(
        r'%l|<layer>|<renderlayer>', re.IGNORECASE)
    R_CAMERA_TOKEN = re.compile(r'%c|<camera>', re.IGNORECASE)
    R_SCENE_TOKEN = re.compile(r'%s|<scene>', re.IGNORECASE)

    DEFAULT_PADDING = 4
    VRAY_PREFIX = "maya/<scene>/<Layer>/<Layer>"
    DEFAULT_PREFIX = "maya/<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        assert invalid is False, ("Invalid render settings "
                                  "found for '{}'!".format(instance.name))

    @classmethod
    def get_invalid(cls, instance):

        invalid = False

        renderer = instance.data['renderer']
        layer = instance.data['setMembers']
        cameras = instance.data.get("cameras", [])

        # Get the node attributes for current renderer
        attrs = lib.RENDER_ATTRS.get(renderer, lib.RENDER_ATTRS['default'])
        prefix = lib.get_attr_in_layer(cls.ImagePrefixes[renderer],
                                       layer=layer)
        padding = lib.get_attr_in_layer("{node}.{padding}".format(**attrs),
                                        layer=layer)

        anim_override = lib.get_attr_in_layer("defaultRenderGlobals.animation",
                                              layer=layer)
        if not anim_override:
            invalid = True
            cls.log.error("Animation needs to be enabled. Use the same "
                          "frame for start and end to render single frame")

        if not prefix.lower().startswith("maya/<scene>"):
            invalid = True
            cls.log.error("Wrong image prefix [ {} ] - "
                          "doesn't start with: 'maya/<scene>'".format(prefix))

        if not re.search(cls.R_LAYER_TOKEN, prefix):
            invalid = True
            cls.log.error("Wrong image prefix [ {} ] - "
                          "doesn't have: '<renderlayer>' or "
                          "'<layer>' token".format(prefix))

        if not re.search(cls.R_AOV_TOKEN, prefix):
            invalid = True
            cls.log.error("Wrong image prefix [ {} ] - "
                          "doesn't have: '<renderpass>' or "
                          "'<aov>' token".format(prefix))

        if len(cameras) > 1:
            if not re.search(cls.R_CAMERA_TOKEN, prefix):
                invalid = True
                cls.log.error("Wrong image prefix [ {} ] - "
                              "doesn't have: '<camera>' token".format(prefix))

        if renderer == "vray":
            if prefix.lower() != cls.VRAY_PREFIX.lower():
                cls.log.warning("warning: prefix differs from "
                                "recommended {}".format(cls.VRAY_PREFIX))
        else:
            if prefix.lower() != cls.DEFAULT_PREFIX.lower():
                cls.log.warning("warning: prefix differs from "
                                "recommended {}".format(cls.DEFAULT_PREFIX))

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
