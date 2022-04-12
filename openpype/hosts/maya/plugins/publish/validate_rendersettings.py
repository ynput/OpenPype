# -*- coding: utf-8 -*-
"""Maya validator for render settings."""
import re
from collections import OrderedDict

from maya import cmds, mel

import pyblish.api
import openpype.api
from openpype.hosts.maya.api import lib


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

    order = openpype.api.ValidateContentsOrder
    label = "Render Settings"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [openpype.api.RepairAction]

    ImagePrefixes = {
        'mentalray': 'defaultRenderGlobals.imageFilePrefix',
        'vray': 'vraySettings.fileNamePrefix',
        'arnold': 'defaultRenderGlobals.imageFilePrefix',
        'renderman': 'rmanGlobals.imageFileFormat',
        'redshift': 'defaultRenderGlobals.imageFilePrefix'
    }

    ImagePrefixTokens = {

        'arnold': 'maya/<Scene>/<RenderLayer>/<RenderLayer>{aov_separator}<RenderPass>',  # noqa
        'redshift': 'maya/<Scene>/<RenderLayer>/<RenderLayer>',
        'vray': 'maya/<Scene>/<Layer>/<Layer>',
        'renderman': '<layer>{aov_separator}<aov>.<f4>.<ext>'  # noqa
    }

    _aov_chars = {
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }

    redshift_AOV_prefix = "<BeautyPath>/<BeautyFile>{aov_separator}<RenderPass>"  # noqa: E501

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

        prefix = prefix.replace(
            "{aov_separator}", instance.data.get("aovSeparator", "_"))

        required_prefix = "maya/<scene>"

        if renderer == "renderman":
            # renderman has prefix set differently
            required_prefix = "<ws>/renders/{}".format(required_prefix)

        if not anim_override:
            invalid = True
            cls.log.error("Animation needs to be enabled. Use the same "
                          "frame for start and end to render single frame")

        if not prefix.lower().startswith(required_prefix):
            invalid = True
            cls.log.error(
                "Wrong image prefix [ {} ] - doesn't start with: '{}'".format(
                    prefix, required_prefix)
            )

        if not re.search(cls.R_LAYER_TOKEN, prefix):
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
                "{aov_separator}", instance.data.get("aovSeparator", "_")
            )
            if re.search(cls.R_AOV_TOKEN, prefix):
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

            if dir_prefix.lower() != cls.RendermanDirPrefix.lower():
                invalid = True
                cls.log.error("Wrong directory prefix [ {} ]".format(
                    dir_prefix))

        if renderer == "arnold":
            multipart = cmds.getAttr("defaultArnoldDriver.mergeAOVs")
            if multipart:
                if re.search(cls.R_AOV_TOKEN, prefix):
                    invalid = True
                    cls.log.error("Wrong image prefix [ {} ] - "
                                  "You can't use '<renderpass>' token "
                                  "with merge AOVs turned on".format(prefix))
            elif not re.search(cls.R_AOV_TOKEN, prefix):
                invalid = True
                cls.log.error("Wrong image prefix [ {} ] - "
                              "doesn't have: '<renderpass>' or "
                              "token".format(prefix))

        # prefix check
        default_prefix = cls.ImagePrefixTokens[renderer]
        default_prefix = default_prefix.replace(
            "{aov_separator}", instance.data.get("aovSeparator", "_"))
        if prefix.lower() != default_prefix.lower():
            cls.log.warning("warning: prefix differs from "
                            "recommended {}".format(
                                default_prefix))

        if padding != cls.DEFAULT_PADDING:
            invalid = True
            cls.log.error("Expecting padding of {} ( {} )".format(
                cls.DEFAULT_PADDING, "0" * cls.DEFAULT_PADDING))

        # load validation definitions from settings
        validation_settings = (
            instance.context.data["project_settings"]["maya"]["publish"]["ValidateRenderSettings"].get(  # noqa: E501
                "{}_render_attributes".format(renderer))
        )

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
                try:
                    render_value = cmds.getAttr(
                        "{}.{}".format(node, attribute_name))
                except RuntimeError:
                    invalid = True
                    cls.log.error(
                        "Cannot get value of {}.{}".format(
                            node, attribute_name))
                else:
                    if str(value) != str(render_value):
                        invalid = True
                        cls.log.error(
                            ("Invalid value {} set on {}.{}. "
                             "Expecting {}").format(
                                render_value, node, attribute_name, value)
                        )

        return invalid

    @classmethod
    def repair(cls, instance):
        renderer = instance.data['renderer']
        layer_node = instance.data['setMembers']
        redshift_AOV_prefix = cls.redshift_AOV_prefix.replace(
            "{aov_separator}", instance.data.get("aovSeparator", "_")
        )
        default_prefix = cls.ImagePrefixTokens[renderer].replace(
            "{aov_separator}", instance.data.get("aovSeparator", "_")
        )

        with lib.renderlayer(layer_node):
            default = lib.RENDER_ATTRS['default']
            render_attrs = lib.RENDER_ATTRS.get(renderer, default)

            # Repair prefix
            if renderer != "renderman":
                node = render_attrs["node"]
                prefix_attr = render_attrs["prefix"]

                fname_prefix = default_prefix
                cmds.setAttr("{}.{}".format(node, prefix_attr),
                             fname_prefix, type="string")

                # Repair padding
                padding_attr = render_attrs["padding"]
                cmds.setAttr("{}.{}".format(node, padding_attr),
                             cls.DEFAULT_PADDING)
            else:
                # renderman handles stuff differently
                cmds.setAttr("rmanGlobals.imageFileFormat",
                             default_prefix,
                             type="string")
                cmds.setAttr("rmanGlobals.imageOutputDir",
                             cls.RendermanDirPrefix,
                             type="string")

            if renderer == "vray":
                vray_settings = cmds.ls(type="VRaySettingsNode")
                if not vray_settings:
                    node = cmds.createNode("VRaySettingsNode")
                else:
                    node = vray_settings[0]

                cmds.optionMenuGrp("vrayRenderElementSeparator",
                                   v=instance.data.get("aovSeparator", "_"))
                cmds.setAttr(
                    "{}.fileNameRenderElementSeparator".format(
                        node),
                    instance.data.get("aovSeparator", "_"),
                    type="string"
                )

            if renderer == "redshift":
                # get redshift AOVs
                rs_aovs = cmds.ls(type="RedshiftAOV", referencedNodes=False)
                for aov in rs_aovs:
                    # fix AOV prefixes
                    cmds.setAttr(
                        "{}.filePrefix".format(aov),
                        redshift_AOV_prefix, type="string")
                    # fix AOV file format
                    default_ext = cmds.getAttr(
                        "redshiftOptions.imageFormat", asString=True)
                    cmds.setAttr(
                        "{}.fileFormat".format(aov), default_ext)
