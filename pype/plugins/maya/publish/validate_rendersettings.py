import os
import re

from maya import cmds, mel
import pymel.core as pm

import pyblish.api
import pype.api
from pype.hosts.maya import lib


class ValidateRenderSettings(pyblish.api.InstancePlugin):
    """Validates the global render settings

    * File Name Prefix must start with: `maya/<Scene>`
        all other token are customizable but sane values for Arnold are:

        `maya/<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>`

        <Camera> token is supported also, useful for multiple renderable
        cameras per render layer.

        For Redshift omit <RenderPass> token. Redshift will append it
        automatically if AOVs are enabled and if you user Multipart EXR
        it doesn't make much sense.

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
        'renderman': 'rmanGlobals.imageFileFormat',
        'redshift': 'defaultRenderGlobals.imageFilePrefix'
    }

    ImagePrefixTokens = {

        'arnold': 'maya/<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>',
        'redshift': 'maya/<Scene>/<RenderLayer>/<RenderLayer>',
        'vray': 'maya/<Scene>/<Layer>/<Layer>',
        'renderman': '<layer>_<aov>.<f4>.<ext>'
    }

    # WARNING: There is bug? in renderman, translating <scene> token
    # to something left behind mayas default image prefix. So instead
    # `SceneName_v01` it translates to:
    # `SceneName_v01/<RenderLayer>/<RenderLayers_<RenderPass>` that means
    # for example:
    # `SceneName_v01/Main/Main_<RenderPass>`. Possible solution is to define
    # custom token like <scene_name> to point to determined scene name.
    RendermanDirPrefix = "<ws>/renders/maya/<scene>/<layer>"

    R_AOV_TOKEN = re.compile(
        r'%a|<aov>|<renderpass>', re.IGNORECASE)
    R_LAYER_TOKEN = re.compile(
        r'%l|<layer>|<renderlayer>', re.IGNORECASE)
    R_CAMERA_TOKEN = re.compile(r'%c|<camera>', re.IGNORECASE)
    R_SCENE_TOKEN = re.compile(r'%s|<scene>', re.IGNORECASE)

    DEFAULT_PADDING = 4
    VRAY_PREFIX = "maya/<Scene>/<Layer>/<Layer>"
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

        if len(cameras) > 1:
            if not re.search(cls.R_CAMERA_TOKEN, prefix):
                invalid = True
                cls.log.error("Wrong image prefix [ {} ] - "
                              "doesn't have: '<camera>' token".format(prefix))

        # renderer specific checks
        if renderer == "vray":
            # no vray checks implemented yet
            pass
        elif renderer == "redshift":
            if re.search(cls.R_AOV_TOKEN, prefix):
                invalid = True
                cls.log.error("Do not use AOV token [ {} ] - "
                              "Redshift automatically append AOV name and "
                              "it doesn't make much sense with "
                              "Multipart EXR".format(prefix))

        elif renderer == "renderman":
            file_prefix = cmds.getAttr("rmanGlobals.imageFileFormat")
            dir_prefix = cmds.getAttr("rmanGlobals.imageOutputDir")

            if file_prefix.lower() != cls.ImagePrefixTokens[renderer].lower():
                invalid = True
                cls.log.error("Wrong image prefix [ {} ]".format(file_prefix))

            if dir_prefix.lower() != cls.RendermanDirPrefix.lower():
                invalid = True
                cls.log.error("Wrong directory prefix [ {} ]".format(
                    dir_prefix))

        else:
            multipart = cmds.getAttr("defaultArnoldDriver.mergeAOVs")
            if multipart:
                if re.search(cls.R_AOV_TOKEN, prefix):
                    invalid = True
                    cls.log.error("Wrong image prefix [ {} ] - "
                                  "You can't use '<renderpass>' token "
                                  "with merge AOVs turned on".format(prefix))
            else:
                if not re.search(cls.R_AOV_TOKEN, prefix):
                    invalid = True
                    cls.log.error("Wrong image prefix [ {} ] - "
                                  "doesn't have: '<renderpass>' or "
                                  "token".format(prefix))

        # prefix check
        if prefix.lower() != cls.ImagePrefixTokens[renderer].lower():
            cls.log.warning("warning: prefix differs from "
                            "recommended {}".format(
                                cls.ImagePrefixTokens[renderer]))

        if padding != cls.DEFAULT_PADDING:
            invalid = True
            cls.log.error("Expecting padding of {} ( {} )".format(
                cls.DEFAULT_PADDING, "0" * cls.DEFAULT_PADDING))

        return invalid

    @classmethod
    def repair(cls, instance):

        renderer = instance.data['renderer']
        layer_node = instance.data['setMembers']

        with lib.renderlayer(layer_node):
            default = lib.RENDER_ATTRS['default']
            render_attrs = lib.RENDER_ATTRS.get(renderer, default)

            # Repair prefix
            if renderer != "renderman":
                node = render_attrs["node"]
                prefix_attr = render_attrs["prefix"]

                fname_prefix = cls.ImagePrefixTokens[renderer]
                cmds.setAttr("{}.{}".format(node, prefix_attr),
                             fname_prefix, type="string")

                # Repair padding
                padding_attr = render_attrs["padding"]
                cmds.setAttr("{}.{}".format(node, padding_attr),
                             cls.DEFAULT_PADDING)
            else:
                # renderman handles stuff differently
                cmds.setAttr("rmanGlobals.imageFileFormat",
                             cls.ImagePrefixTokens[renderer],
                             type="string")
                cmds.setAttr("rmanGlobals.imageOutputDir",
                             cls.RendermanDirPrefix,
                             type="string")
