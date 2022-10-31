# -*- coding: utf-8 -*-
"""Class for handling Render Settings."""
from maya import cmds  # noqa
import maya.mel as mel
import six
import sys
import re

from openpype.lib import Logger
from openpype.settings import (
    get_project_settings,
    get_current_project_settings
)

from openpype.pipeline import legacy_io
from openpype.pipeline import CreatorError
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.hosts.maya.api.commands import reset_frame_range


class RenderSettings(object):

    _image_prefix_nodes = {
        'vray': 'vraySettings.fileNamePrefix',
        'arnold': 'defaultRenderGlobals.imageFilePrefix',
        'renderman': 'defaultRenderGlobals.imageFilePrefix',
        'redshift': 'defaultRenderGlobals.imageFilePrefix',
        '_3delight': 'defaultRenderGlobals.imageFilePrefix'
    }

    _image_prefixes = {
        'vray': get_current_project_settings()["maya"]["RenderSettings"]["vray_renderer"]["image_prefix"],  # noqa
        'arnold': get_current_project_settings()["maya"]["RenderSettings"]["arnold_renderer"]["image_prefix"],  # noqa
        'renderman': '<Scene>/<layer>/<layer>{aov_separator}<aov>',
        'redshift': get_current_project_settings()["maya"]["RenderSettings"]["redshift_renderer"]["image_prefix"],  # noqa
        '_3delight': '<Scene>/<layer>/<layer>{aov_separator}<aov>'
    }

    _aov_chars = {
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }

    log = Logger.get_logger("RenderSettings")

    @classmethod
    def get_image_prefix_attr(cls, renderer):
        return cls._image_prefix_nodes[renderer]

    def __init__(self, project_settings=None):
        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_project_settings(
                legacy_io.Session["AVALON_PROJECT"]
            )

    def set_default_renderer_settings(self, renderer=None):
        """Set basic settings based on renderer."""
        if not renderer:
            renderer = cmds.getAttr(
                'defaultRenderGlobals.currentRenderer').lower()

        asset_doc = get_current_project_asset()
        # project_settings/maya/create/CreateRender/aov_separator
        try:
            aov_separator = self._aov_chars[(
                self._project_settings["maya"]
                                      ["RenderSettings"]
                                      ["aov_separator"]
            )]
        except KeyError:
            aov_separator = "_"
        reset_frame = self._project_settings["maya"]["RenderSettings"]["reset_current_frame"]  # noqa

        if reset_frame:
            start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
            cmds.currentTime(start_frame, edit=True)

        if renderer in self._image_prefix_nodes:
            prefix = self._image_prefixes[renderer]
            prefix = prefix.replace("{aov_separator}", aov_separator)
            cmds.setAttr(self._image_prefix_nodes[renderer],
                        prefix, type="string")  # noqa
        else:
            print("{0} isn't a supported renderer to autoset settings.".format(renderer))  # noqa

        # TODO: handle not having res values in the doc
        width = asset_doc["data"].get("resolutionWidth")
        height = asset_doc["data"].get("resolutionHeight")

        if renderer == "arnold":
            # set renderer settings for Arnold from project settings
            self._set_arnold_settings(width, height)

        if renderer == "vray":
            self._set_vray_settings(aov_separator, width, height)

        if renderer == "redshift":
            self._set_redshift_settings(width, height)

        if renderer == "_3delight":
            self._set_3delight_settings(width, height)

    def _set_arnold_settings(self, width, height):
        """Sets settings for Arnold."""
        from mtoa.core import createOptions  # noqa
        from mtoa.aovs import AOVInterface  # noqa
        createOptions()
        arnold_render_presets = self._project_settings["maya"]["RenderSettings"]["arnold_renderer"]  # noqa
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
        img_prefix = arnold_render_presets["image_prefix"]
        aovs = arnold_render_presets["aov_list"]
        img_tiled = arnold_render_presets["tiled"]
        multi_exr = arnold_render_presets["multilayer_exr"]
        additional_options = arnold_render_presets["additional_options"]
        for aov in aovs:
            AOVInterface('defaultArnoldRenderOptions').addAOV(aov)

        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)

        self._set_global_output_settings()

        cmds.setAttr(
            "defaultRenderGlobals.imageFilePrefix", img_prefix, type="string")

        cmds.setAttr(
            "defaultArnoldDriver.ai_translator", img_ext, type="string")

        cmds.setAttr(
            "defaultArnoldDriver.exrTiled", img_tiled)

        cmds.setAttr(
            "defaultArnoldDriver.mergeAOVs", multi_exr)
        self._additional_attribs_setter(additional_options)
        reset_frame_range()

    def _set_redshift_settings(self, width, height):
        """Sets settings for Redshift."""
        redshift_render_presets = (
            self._project_settings
            ["maya"]
            ["RenderSettings"]
            ["redshift_renderer"]
        )
        additional_options = redshift_render_presets["additional_options"]
        ext = redshift_render_presets["image_format"]
        img_exts = ["iff", "exr", "tif", "png", "tga", "jpg"]
        img_ext = img_exts.index(ext)

        self._set_global_output_settings()
        cmds.setAttr("redshiftOptions.imageFormat", img_ext)
        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)
        self._additional_attribs_setter(additional_options)

    def _set_vray_settings(self, aov_separator, width, height):
        # type: (str, int, int) -> None
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
        for item in additional_attribs:
            attribute, value = item
            attribute = str(attribute)  # ensure str conversion from settings
            attribute_type = cmds.getAttr(attribute, type=True)
            if attribute_type in {"long", "bool"}:
                cmds.setAttr(attribute, int(value))
            elif attribute_type == "string":
                cmds.setAttr(attribute, str(value), type="string")
            elif attribute_type in {"double", "doubleAngle", "doubleLinear"}:
                cmds.setAttr(attribute, float(value))
            else:
                self.log.error(
                    "Attribute {attribute} can not be set due to unsupported "
                    "type: {attribute_type}".format(
                        attribute=attribute,
                        attribute_type=attribute_type)
                )

    def _set_3delight_settings(self, width, height):
        """Sets important settings for 3Delight. """

        # resolution
        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)
        cmds.setAttr("defaultRenderGlobals.animation", 1)

        # frame range
        start_frame = int(cmds.playbackOptions(query=True,
                                               animationStartTime=True))
        end_frame = int(cmds.playbackOptions(query=True,
                                             animationEndTime=True))

        dl_render_settings = cmds.ls(type="dlRenderSettings")
        assert len(dl_render_settings) >= 1
        for dl_render_setting in dl_render_settings:
            cmds.setAttr(
                "{}.startFrame".format(dl_render_setting), start_frame)
            cmds.setAttr(
                "{}.endFrame".format(dl_render_setting), end_frame)

            # outputOptionsDefault
            cmds.setAttr(
                "{}.outputOptionsDefault".format(dl_render_setting), 2)

        """
        3delight doesn't use maya's render layers to indicate what to render,
        instead, it uses dlRenderSettings as specified by the connection to
        dlRenderGlobals1, of which there is only one. Since this is not the
        "mayaonic" way, we must insert a pre-render MEL into maya's
        "defaultRenderGlobals.preMel", which will help us work this out. We
        wouldn't this this ... "hack" if deadline allowed us to insert commands
        into its MayaBatch stuff, or, if it allowed setting up renderers in a
        sensible way.
        """

        # We need the DOTALL since the regex will now match across newlines.
        regex_match = re.compile(r"\/\*--\*3dl_v\d+\*--\*\/.*\/\*--\*\*--\*\/",
                                 re.DOTALL)
        PREMEL_TEMPLATE = """/*--*3dl_v4*--*/
currentTime -e `getAttr ("defaultRenderGlobals.startFrame")`;
string $lsCon[] = `listConnections renderLayerManager.renderLayerId`;
for ($i = 0 ; $i<size($lsCon) ; $i++)
{
    string $cl = $lsCon[$i];
    if (!startsWith($cl, "rs_"))
        continue;
    if (!endsWith($cl, "_RL"))
        continue;
    string $_3l = substring($cl, 4, size($cl)-3);
    if (getAttr($cl+".renderable"))
    {
        string $rg = "dlRenderGlobals1.renderSettings";
        DL_disconnectNode( $rg );
        DL_connectNodeToMessagePlug( $_3l, $rg );
        setAttr($_3l+".startFrame",
            `getAttr ("defaultRenderGlobals.startFrame")`);
        setAttr($_3l+".endFrame",
            `getAttr ("defaultRenderGlobals.endFrame")`);
        setAttr($_3l+".isRenderingSequence", 1);
    }
}
/*--**--*/"""

        preMel = cmds.getAttr("defaultRenderGlobals.preMel")
        print("This is our current 'preMel':[{}]".format(preMel))
        if preMel is None:
            print("  - we need to insert our own preMel")
            preMel = PREMEL_TEMPLATE
        else:
            print("  - we have preMel update it")
            preMel = re.sub(regex_match, PREMEL_TEMPLATE, preMel)

        cmds.setAttr("defaultRenderGlobals.preMel", preMel, type="string")
