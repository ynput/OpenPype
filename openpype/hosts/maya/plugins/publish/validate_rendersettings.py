# -*- coding: utf-8 -*-
"""Maya validator for render settings."""
import re
from collections import OrderedDict

from maya import cmds, mel

import pyblish.api
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
)
from openpype.hosts.maya.api import lib
from openpype.hosts.maya.api.lib_rendersettings import RenderSettings
from openpype.hosts.maya.api.lib_renderproducts import (
    R_AOV_TOKEN,
    R_LAYER_TOKEN
)


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

    order = ValidateContentsOrder
    label = "Render Settings"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [RepairAction]

    redshift_AOV_prefix = "<BeautyPath>/<BeautyFile>{aov_separator}<RenderPass>"  # noqa: E501

    renderman_dir_prefix = "maya/<scene>/<layer>"

    R_CAMERA_TOKEN = re.compile(r'%c|Camera>')
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
        multipart = False

        renderer = instance.data['renderer']
        layer = instance.data['setMembers']
        cameras = instance.data.get("cameras", [])

        render_settings = RenderSettings(
            project_settings=instance.context.data["project_settings"])

        # Get current image prefix and padding set in scene
        prefix = lib.get_attr_in_layer(
            render_settings.get_image_prefix_attr(renderer), layer=layer)
        padding = lib.get_attr_in_layer(
            render_settings.get_padding_attr(renderer), layer=layer)

        anim_override = lib.get_attr_in_layer("defaultRenderGlobals.animation",
                                              layer=layer)

        prefix = prefix.replace(
            "{aov_separator}", instance.data.get("aovSeparator", "_"))

        default_prefix = render_settings.get_default_image_prefix(
            renderer, format_aov_separator=False)
        aov_separator = render_settings.get_aov_separator()

        if not anim_override:
            invalid = True
            cls.log.error("Animation needs to be enabled. Use the same "
                          "frame for start and end to render single frame")

        if not re.search(R_LAYER_TOKEN, prefix):
            invalid = True
            cls.log.error("Wrong image prefix [ {} ] - "
                          "doesn't have: '<renderlayer>' or "
                          "'<layer>' token".format(prefix))

        if len(cameras) > 1 and not re.search(cls.R_CAMERA_TOKEN, prefix):
            invalid = True
            cls.log.error("Wrong image prefix [ {} ] - "
                          "doesn't have: '<Camera>' token".format(prefix))
            cls.log.error(
                "Note that to needs to have capital 'C' at the beginning")

        # renderer specific checks
        if renderer == "vray":
            vray_settings = cmds.ls(type="VRaySettingsNode")
            if not vray_settings:
                node = cmds.createNode("VRaySettingsNode")
            else:
                node = vray_settings[0]

            scene_sep = cmds.getAttr(
                "{}.fileNameRenderElementSeparator".format(node))
            if scene_sep != instance.data.get("aovSeparator", "_"):
                cls.log.error("AOV separator is not set correctly.")
                invalid = True

        if renderer == "redshift":
            redshift_AOV_prefix = cls.redshift_AOV_prefix.replace(
                "{aov_separator}", aov_separator
            )
            if re.search(R_AOV_TOKEN, prefix):
                invalid = True
                cls.log.error(("Do not use AOV token [ {} ] - "
                               "Redshift is using image prefixes per AOV so "
                               "it doesn't make much sense using it in global"
                               "image prefix").format(prefix))
            # get redshift AOVs
            rs_aovs = cmds.ls(type="RedshiftAOV", referencedNodes=False)
            for aov in rs_aovs:
                aov_prefix = cmds.getAttr("{}.filePrefix".format(aov))
                # check their image prefix
                if aov_prefix != redshift_AOV_prefix:
                    cls.log.error(("AOV ({}) image prefix is not set "
                                   "correctly {} != {}").format(
                        cmds.getAttr("{}.name".format(aov)),
                        aov_prefix,
                        redshift_AOV_prefix
                    ))
                    invalid = True
                # get aov format
                aov_ext = cmds.getAttr(
                    "{}.fileFormat".format(aov), asString=True)

                default_ext = cmds.getAttr(
                    "redshiftOptions.imageFormat", asString=True)

                if default_ext != aov_ext:
                    cls.log.error(("AOV file format is not the same "
                                   "as the one set globally "
                                   "{} != {}").format(default_ext,
                                                      aov_ext))
                    invalid = True

        if renderer == "renderman":
            file_prefix = cmds.getAttr("rmanGlobals.imageFileFormat")
            dir_prefix = cmds.getAttr("rmanGlobals.imageOutputDir")

            if file_prefix.lower() != prefix.lower():
                invalid = True
                cls.log.error("Wrong image prefix [ {} ]".format(file_prefix))

            if dir_prefix.lower() != cls.renderman_dir_prefix.lower():
                invalid = True
                cls.log.error("Wrong directory prefix [ {} ]".format(
                    dir_prefix))

        if renderer == "arnold":
            multipart = cmds.getAttr("defaultArnoldDriver.mergeAOVs")
            multipart_default = render_settings.get(
                "arnold_renderer/multilayer_exr", True)
            if multipart != multipart_default:
                cls.log.warning("Warning: Merge AOVs differs from project "
                                "recommended: {}".format(multipart_default))

            if multipart:
                if re.search(R_AOV_TOKEN, prefix):
                    invalid = True
                    cls.log.error("Wrong image prefix [ {} ] - "
                                  "You can't use '<renderpass>' token "
                                  "with merge AOVs turned on".format(prefix))
            elif not re.search(R_AOV_TOKEN, prefix):
                invalid = True
                cls.log.error("Wrong image prefix [ {} ] - "
                              "You must have: '<renderpass>' token "
                              "with merge AOVs turned off".format(prefix))

        default_prefix = default_prefix.replace("{aov_separator}",
                                                aov_separator)
        if prefix.lower() != default_prefix.lower():
            cls.log.warning("Warning: prefix differs from "
                            "recommended {}".format(default_prefix))

        if padding != cls.DEFAULT_PADDING:
            invalid = True
            cls.log.error("Expecting padding of {} ( {} )".format(
                cls.DEFAULT_PADDING, "0" * cls.DEFAULT_PADDING))

        # load validation definitions from settings
        validation_settings = (
            instance.context.data["project_settings"]["maya"]["publish"]["ValidateRenderSettings"].get(  # noqa: E501
                "{}_render_attributes".format(renderer)) or []
        )
        settings_lights_flag = instance.context.data["project_settings"].get(
            "maya", {}).get(
            "RenderSettings", {}).get(
            "enable_all_lights", False)

        instance_lights_flag = instance.data.get("renderSetupIncludeLights")
        if settings_lights_flag != instance_lights_flag:
            cls.log.warning('Instance flag for "Render Setup Include Lights" is set to {0} and Settings flag is set to {1}'.format(instance_lights_flag, settings_lights_flag)) # noqa

        # go through definitions and test if such node.attribute exists.
        # if so, compare its value from the one required.
        for attr, value in OrderedDict(validation_settings).items():
            # first get node of that type
            cls.log.debug("{}: {}".format(attr, value))
            node_type = attr.split(".")[0]
            attribute_name = ".".join(attr.split(".")[1:])
            nodes = cmds.ls(type=node_type)

            if not isinstance(nodes, list):
                cls.log.warning("No nodes of '{}' found.".format(node_type))
                continue

            for node in nodes:
                plug = "{}.{}".format(node, attribute_name)
                try:
                    render_value = cmds.getAttr(plug)
                except RuntimeError:
                    invalid = True
                    cls.log.error("Cannot get value of {}".format(plug))
                else:
                    if str(value) != str(render_value):
                        invalid = True
                        cls.log.error(
                            "Invalid value {} set on {}. Expecting {}"
                            "".format(render_value, plug, value)
                        )

        return invalid

    @classmethod
    def repair(cls, instance):
        renderer = instance.data['renderer']
        layer_node = instance.data['setMembers']

        render_settings = RenderSettings(
            project_settings=instance.context.data["project_settings"])

        default_prefix = render_settings.get_default_image_prefix(renderer)
        aov_separator = render_settings.get_aov_separator()

        with lib.renderlayer(layer_node):

            if renderer != "renderman":
                # Repair prefix
                prefix_attr = render_settings.get_image_prefix_attr(renderer)
                cmds.setAttr(prefix_attr, default_prefix, type="string")

                # Repair padding
                padding_attr = render_settings.get_padding_attr(renderer)
                cmds.setAttr(padding_attr, cls.DEFAULT_PADDING)
            else:
                # renderman handles stuff differently
                cmds.setAttr("rmanGlobals.imageFileFormat",
                             default_prefix,
                             type="string")
                cmds.setAttr("rmanGlobals.imageOutputDir",
                             cls.renderman_dir_prefix,
                             type="string")

            # Repair AOV separators
            if renderer == "vray":
                vray_settings = cmds.ls(type="VRaySettingsNode")
                if not vray_settings:
                    node = cmds.createNode("VRaySettingsNode")
                else:
                    node = vray_settings[0]

                cmds.optionMenuGrp("vrayRenderElementSeparator",
                                   v=aov_separator)
                cmds.setAttr(
                    "{}.fileNameRenderElementSeparator".format(node),
                    aov_separator,
                    type="string"
                )

            if renderer == "redshift":
                redshift_AOV_prefix = cls.redshift_AOV_prefix.replace(
                    "{aov_separator}", aov_separator
                )
                # get redshift AOVs
                rs_aovs = cmds.ls(type="RedshiftAOV", referencedNodes=False)
                for aov in rs_aovs:
                    # fix AOV prefixes
                    cmds.setAttr("{}.filePrefix".format(aov),
                                 redshift_AOV_prefix,
                                 type="string")
                    # fix AOV file format
                    default_ext = cmds.getAttr("redshiftOptions.imageFormat",
                                               asString=True)
                    cmds.setAttr("{}.fileFormat".format(aov),
                                 default_ext)
