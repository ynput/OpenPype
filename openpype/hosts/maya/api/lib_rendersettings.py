# -*- coding: utf-8 -*-
"""Class for handling Render Settings."""
from maya import cmds  # noqa
import maya.mel as mel
import six
import sys

from openpype.api import (
    get_current_project_settings
)

from openpype.pipeline import CreatorError
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.hosts.maya.api.commands import reset_frame_range


class RenderSettings(object):

    _image_prefix_nodes = {
        'vray': 'vraySettings.fileNamePrefix',
        'arnold': 'defaultRenderGlobals.imageFilePrefix',
        'renderman': 'defaultRenderGlobals.imageFilePrefix',
        'redshift': 'defaultRenderGlobals.imageFilePrefix',
        'mentalray': 'defaultRenderGlobals.imageFilePrefix',
        'mayahardware2': 'defaultRenderGlobals.imageFilePrefix'
    }

    _aov_chars = {
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }

    def get_aov_separator(self):
        # project_settings/maya/RenderSettings/aov_separator
        try:
            aov_separator = self._aov_chars[(
                self._project_settings["maya"]
                ["RenderSettings"]
                ["aov_separator"]
            )]
        except KeyError:
            aov_separator = "_"
        return aov_separator

    @classmethod
    def get_image_prefix_attr(cls, renderer):
        return cls._image_prefix_nodes[renderer]

    @staticmethod
    def get_padding_attr(renderer):
        if renderer == "vray":
            return "vraySettings.fileNamePadding"
        else:
            return "defaultRenderGlobals.extensionPadding"

    def get_default_image_prefix(self, renderer, format_aov_separator=True):
        """Get image prefix rule for the renderer from project settings

        When `format_aov_separator` is not enabled the {aov_separator} token
        will be preserved from settings.

        """
        # project_settings/maya/RenderSettings/{renderer}_renderer/image_prefix

        def _format_prefix(prefix):
            """Format `{aov_separator}` in prefix.

            Only does something if `format_aov_separator` is enabled
            """
            if format_aov_separator:
                prefix = prefix.replace("{aov_separator}",
                                        self.get_aov_separator())
            return prefix

        # todo: do not hardcode, implement in settings
        hardcoded_prefixes = {
            "renderman": 'maya/<Scene>/<layer>/<layer>{aov_separator}<aov>',
            'mentalray': 'maya/<Scene>/<RenderLayer>/<RenderLayer>{aov_separator}<RenderPass>',  # noqa: E501
            'mayahardware2': 'maya/<Scene>/<RenderLayer>/<RenderLayer>',
        }
        if renderer in hardcoded_prefixes:
            prefix = hardcoded_prefixes[renderer]
            return _format_prefix(prefix)

        render_settings = self._project_settings["maya"]["RenderSettings"]
        renderer_key = "{}_renderer".format(renderer)
        if renderer_key not in render_settings:
            print("Renderer {} has no render "
                  "settings implementation.".format(renderer))
            return

        renderer_settings = render_settings[renderer_key]
        renderer_image_prefix = renderer_settings.get("image_prefix")
        if renderer_image_prefix is None:
            print("Renderer {} has no image prefix setting.".format(renderer))
            return

        return _format_prefix(renderer_image_prefix)

    def __init__(self, project_settings=None):
        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_current_project_settings()

    def set_default_renderer_settings(self, renderer=None):
        """Set basic settings based on renderer."""
        if not renderer:
            renderer = cmds.getAttr(
                'defaultRenderGlobals.currentRenderer').lower()

        asset_doc = get_current_project_asset()
        # TODO: handle not having res values in the doc
        width = asset_doc["data"].get("resolutionWidth")
        height = asset_doc["data"].get("resolutionHeight")

        # Set renderer specific settings first because some might reset
        # renderer defaults and thus override e.g. prefixes, etc.
        if renderer == "arnold":
            self._set_arnold_settings(width, height)
        elif renderer == "vray":
            self._set_vray_settings(width, height)
        elif renderer == "redshift":
            self._set_redshift_settings(width, height)

        # Set global output settings
        self._set_global_output_settings()

        # Reset current frame
        reset_frame = self._project_settings["maya"]["RenderSettings"]["reset_current_frame"] # noqa
        if reset_frame:
            start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
            cmds.currentTime(start_frame, edit=True)

        # Set image file prefix
        prefix = self.get_default_image_prefix(renderer,
                                               format_aov_separator=True)
        if prefix:
            attr = self.get_image_prefix_attr(renderer)
            cmds.setAttr(attr, prefix, type="string")

    def _set_arnold_settings(self, width, height):
        """Sets settings for Arnold."""
        from mtoa.core import createOptions  # noqa
        from mtoa.aovs import AOVInterface  # noqa
        createOptions()
        arnold_render_presets = self._project_settings["maya"]["RenderSettings"]["arnold_renderer"] # noqa
        # Force resetting settings and AOV list to avoid having to deal with
        # AOV checking logic, for now.
        # This is a work around because the standard
        # function to revert render settings does not reset AOVs list in MtoA
        # Fetch current aovs in case there's any.
        current_aovs = AOVInterface().getAOVs()
        # Remove fetched AOVs
        AOVInterface().removeAOVs(current_aovs)
        mel.eval("unifiedRenderGlobalsRevertToDefault")
        img_ext = arnold_render_presets["image_format"]
        aovs = arnold_render_presets["aov_list"]
        img_tiled = arnold_render_presets["tiled"]
        multi_exr = arnold_render_presets["multilayer_exr"]
        for aov in aovs:
            AOVInterface('defaultArnoldRenderOptions').addAOV(aov)

        cmds.setAttr(
            "defaultArnoldDriver.ai_translator", img_ext, type="string")

        cmds.setAttr(
            "defaultArnoldDriver.exrTiled", img_tiled)

        cmds.setAttr(
            "defaultArnoldDriver.mergeAOVs", multi_exr)
        # Passes additional options in from the schema as a list
        # but converts it to a dictionary because ftrack doesn't
        # allow fullstops in custom attributes. Then checks for
        # type of MtoA attribute passed to adjust the `setAttr`
        # command accordingly.
        self._additional_attribs_setter(additional_options)
        for item in additional_options:
            attribute, value = item
            if (cmds.getAttr(str(attribute), type=True)) == "long":
                cmds.setAttr(str(attribute), int(value))
            elif (cmds.getAttr(str(attribute), type=True)) == "bool":
                cmds.setAttr(str(attribute), int(value), type = "Boolean") # noqa
            elif (cmds.getAttr(str(attribute), type=True)) == "string":
                cmds.setAttr(str(attribute), str(value), type = "string") # noqa
        reset_frame_range()

    def _set_redshift_settings(self, width, height):
        """Sets settings for Redshift."""
        redshift_render_presets = (
            self._project_settings
            ["maya"]
            ["RenderSettings"]
            ["redshift_renderer"]
        )
        ext = redshift_render_presets["image_format"]

        # Set image format
        img_exts = ["iff", "exr", "tif", "png", "tga", "jpg"]
        img_ext = img_exts.index(ext)
        cmds.setAttr("redshiftOptions.imageFormat", img_ext)

        additional_options = redshift_render_presets["additional_options"]
        self._additional_attribs_setter(additional_options)

    def _set_vray_settings(self, width, height):
        # type: (int, int) -> None
        """Sets important settings for Vray."""
        settings = cmds.ls(type="VRaySettingsNode")
        node = settings[0] if settings else cmds.createNode("VRaySettingsNode")
        vray_render_presets = (
            self._project_settings
            ["maya"]
            ["RenderSettings"]
            ["vray_renderer"]
        )
        # Set aov separator
        # First we need to explicitly set the UI items in Render Settings
        # because that is also what V-Ray updates to when that Render Settings
        # UI did initialize before and refreshes again.
        aov_separator = self.get_aov_separator()
        MENU = "vrayRenderElementSeparator"
        if cmds.optionMenuGrp(MENU, query=True, exists=True):
            items = cmds.optionMenuGrp(MENU, query=True, ill=True)
            separators = [cmds.menuItem(i, query=True, label=True) for i in items]  # noqa: E501
            try:
                sep_idx = separators.index(aov_separator)
            except ValueError as e:
                six.reraise(
                    CreatorError,
                    CreatorError(
                        "AOV character {} not in {}".format(
                            aov_separator, separators)),
                    sys.exc_info()[2])

            cmds.optionMenuGrp(MENU, edit=True, select=sep_idx + 1)

        # Set the render element attribute as string. This is also what V-Ray
        # sets whenever the `vrayRenderElementSeparator` menu items switch
        cmds.setAttr(
            "{}.fileNameRenderElementSeparator".format(node),
            aov_separator,
            type="string"
        )

        # Set render file format to exr
        cmds.setAttr("{}.imageFormatStr".format(node), "exr", type="string")

        # animType
        cmds.setAttr("{}.animType".format(node), 1)

        # resolution
        cmds.setAttr("{}.width".format(node), width)
        cmds.setAttr("{}.height".format(node), height)

        additional_options = vray_render_presets["additional_options"]
        self._additional_attribs_setter(additional_options)

    @staticmethod
    def _set_global_output_settings():
        # enable animation
        cmds.setAttr("defaultRenderGlobals.outFormatControl", 0)
        cmds.setAttr("defaultRenderGlobals.animation", 1)
        cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", 1)
        cmds.setAttr("defaultRenderGlobals.extensionPadding", 4)

    def _additional_attribs_setter(self, additional_attribs):
        print(additional_attribs)
        for item in additional_attribs:
            attribute, value = item
            if (cmds.getAttr(str(attribute), type=True)) == "long":
                cmds.setAttr(str(attribute), int(value))
            elif (cmds.getAttr(str(attribute), type=True)) == "bool":
                cmds.setAttr(str(attribute), int(value)) # noqa
            elif (cmds.getAttr(str(attribute), type=True)) == "string":
                cmds.setAttr(str(attribute), str(value), type = "string") # noqa
