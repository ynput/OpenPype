# -*- coding: utf-8 -*-
"""Class for handling Render Settings."""
from maya import cmds  # noqa
import maya.mel as mel
import six
import sys

from openpype.lib import Logger
from openpype.settings import get_current_project_settings

from openpype.pipeline import CreatorError
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.hosts.maya.api.lib import reset_frame_range


class RenderSettings(object):
    """Render Settings defined in OpenPype project settings per renderer.

    Based on the Project Settings this allows you to query and set the render
    setting defaults for the current project.

    The RenderSettings can query the `project_settings/maya/RenderSettings`
    entries by accessing its items. It also allows to get a setting values
    nested down using a forward slash `/` in the item. For example:
        >>> settings = RenderSettings()
        >>> # project_settings/maya/RenderSettings/aov_separator
        >>> settings["aov_separator"]
        >>> # project_settings/maya/RenderSettings/arnold_renderer/image_format
        >>> settings["arnold_renderer/image_format"]
        >>> # or with a default value fallback if setting does not exist
        >>> settings.get("arnold_renderer/image_format", default=True)

    """

    _image_prefix_nodes = {
        "vray": "vraySettings.fileNamePrefix",
        "arnold": "defaultRenderGlobals.imageFilePrefix",
        "renderman": "rmanGlobals.imageFileFormat",
        "redshift": "defaultRenderGlobals.imageFilePrefix",
        "mentalray": "defaultRenderGlobals.imageFilePrefix",
        "mayahardware2": "defaultRenderGlobals.imageFilePrefix"
    }

    _aov_chars = {
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }

    log = Logger.get_logger("RenderSettings")

    def __init__(self, project_settings=None):
        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_current_project_settings()

        # Renderman only image dir
        renderman_settings = self["renderman_renderer"]
        self._image_dir = {
            "renderman": renderman_settings["image_dir"],
            "cryptomatte": renderman_settings["cryptomatte_dir"],
            "imageDisplay": renderman_settings["imageDisplay_dir"],
            "watermark": renderman_settings["watermark_dir"]
        }

    def get_aov_separator(self):
        # project_settings/maya/RenderSettings/aov_separator
        aov_separator_name = self["aov_separator"]
        return self._aov_chars.get(aov_separator_name, "_")

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
            "renderman": "maya/<Scene>/<layer>/<layer>{aov_separator}<aov>",
            "mentalray": "maya/<Scene>/<RenderLayer>/<RenderLayer>{aov_separator}<RenderPass>",  # noqa: E501
            "mayahardware2": "maya/<Scene>/<RenderLayer>/<RenderLayer>",
        }
        if renderer in hardcoded_prefixes:
            prefix = hardcoded_prefixes[renderer]
            return _format_prefix(prefix)

        renderer_key = "{}_renderer".format(renderer)
        if renderer_key not in self:
            print("Renderer {} has no render "
                  "settings implementation.".format(renderer))
            return

        renderer_settings = self[renderer_key]
        renderer_image_prefix = renderer_settings.get("image_prefix")
        if renderer_image_prefix is None:
            print("Renderer {} has no image prefix setting.".format(renderer))
            return

        return _format_prefix(renderer_image_prefix)

    def set_default_renderer_settings(self, renderer=None):
        """Set basic settings based on renderer."""
        if not renderer:
            renderer = cmds.getAttr(
                "defaultRenderGlobals.currentRenderer").lower()

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
            mel.eval("redshiftUpdateActiveAovList")

        if renderer == "renderman":
            image_dir = self._image_dir["renderman"]
            cmds.setAttr("rmanGlobals.imageOutputDir",
                         image_dir, type="string")
            self._set_renderman_settings(width, height)

        # Set global output settings
        self._set_global_output_settings()

        # Reset current frame
        if self["reset_current_frame"]:
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
        arnold_render_presets = self["arnold_renderer"]
        # Force resetting settings and AOV list to avoid having to deal with
        # AOV checking logic, for now.
        # This is a work around because the standard
        # function to revert render settings does not reset AOVs list in MtoA
        # Fetch current aovs in case there's any.
        current_aovs = AOVInterface().getAOVs()
        remove_aovs = self["remove_aovs"]
        if remove_aovs:
            # Remove fetched AOVs
            AOVInterface().removeAOVs(current_aovs)
        mel.eval("unifiedRenderGlobalsRevertToDefault")
        img_ext = arnold_render_presets["image_format"]
        aovs = arnold_render_presets["aov_list"]
        img_tiled = arnold_render_presets["tiled"]
        multi_exr = arnold_render_presets["multilayer_exr"]
        for aov in aovs:
            if aov in current_aovs and not remove_aovs:
                continue
            AOVInterface("defaultArnoldRenderOptions").addAOV(aov)

        cmds.setAttr(
            "defaultArnoldDriver.ai_translator", img_ext, type="string")

        cmds.setAttr(
            "defaultArnoldDriver.exrTiled", img_tiled)

        cmds.setAttr(
            "defaultArnoldDriver.mergeAOVs", multi_exr)

        # When MergeAOV is enabled (=Multilayer EXR) there should be no
        # <renderpass> token and no {aov_separator}. When MergeAOV is disabled
        # both tokens must be present
        prefix = self.get_default_image_prefix("arnold",
                                               format_aov_separator=False)
        aov_tokens = (
            int("{aov_separator}" in prefix) +
            int("<renderpass>" in prefix.lower())
        )
        if multi_exr and aov_tokens > 0:
            self.log.error("Invalid settings found. You can't use "
                           "{{aov_separator}} or <RenderPass> token in Image"
                           "Prefix Template when Multilayer (exr) is enabled:"
                           " {}".format(prefix))
        elif not multi_exr and aov_tokens < 2:
            self.log.error("Invalid settings found. You must use "
                           "{{aov_separator}} and <RenderPass> token in Image "
                           "Prefix Template when Multilayer (exr) is disabled:"
                           " {}".format(prefix))

        additional_options = arnold_render_presets["additional_options"]
        self._additional_attribs_setter(additional_options)

        reset_frame_range(playback=False, fps=False, render=True)

    def _set_redshift_settings(self, width, height):
        """Sets settings for Redshift."""
        redshift_render_presets = self["redshift_renderer"]

        remove_aovs = self["remove_aovs"]
        all_rs_aovs = cmds.ls(type="RedshiftAOV")
        if remove_aovs:
            for aov in all_rs_aovs:
                enabled = cmds.getAttr("{}.enabled".format(aov))
                if enabled:
                    cmds.delete(aov)

        redshift_aovs = redshift_render_presets["aov_list"]
        # list all the aovs
        all_rs_aovs = cmds.ls(type="RedshiftAOV")
        for rs_aov in redshift_aovs:
            if " " in rs_aov:
                rs_renderlayer = rs_aov.replace(" ", "")
                rs_layername = "rsAov_{}".format(rs_renderlayer)
            else:
                rs_layername = "rsAov_{}".format(rs_aov)
            if rs_layername in all_rs_aovs:
                continue
            cmds.rsCreateAov(type=rs_aov)
        # update the AOV list
        mel.eval("redshiftUpdateActiveAovList")

        rs_p_engine = redshift_render_presets["primary_gi_engine"]
        rs_s_engine = redshift_render_presets["secondary_gi_engine"]

        if int(rs_p_engine) or int(rs_s_engine) != 0:
            cmds.setAttr("redshiftOptions.GIEnabled", 1)
            if int(rs_p_engine) == 0:
                # reset the primary GI Engine as default
                cmds.setAttr("redshiftOptions.primaryGIEngine", 4)
            if int(rs_s_engine) == 0:
                # reset the secondary GI Engine as default
                cmds.setAttr("redshiftOptions.secondaryGIEngine", 2)
        else:
            cmds.setAttr("redshiftOptions.GIEnabled", 0)

        cmds.setAttr("redshiftOptions.primaryGIEngine", int(rs_p_engine))
        cmds.setAttr("redshiftOptions.secondaryGIEngine", int(rs_s_engine))

        # Set image format
        ext = redshift_render_presets["image_format"]
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
        vray_render_presets = self["vray_renderer"]

        # vrayRenderElement
        remove_aovs = self["remove_aovs"]
        all_vray_aovs = cmds.ls(type="VRayRenderElement")
        lightSelect_aovs = cmds.ls(type="VRayRenderElementSet")
        if remove_aovs:
            for aov in all_vray_aovs:
                # remove all aovs except LightSelect
                enabled = cmds.getAttr("{}.enabled".format(aov))
                if enabled:
                    cmds.delete(aov)
            # remove LightSelect
            for light_aovs in lightSelect_aovs:
                light_enabled = cmds.getAttr("{}.enabled".format(light_aovs))
                if light_enabled:
                    cmds.delete(lightSelect_aovs)

        vray_aovs = vray_render_presets["aov_list"]
        for renderlayer in vray_aovs:
            renderElement = "vrayAddRenderElement {}".format(renderlayer)
            RE_name = mel.eval(renderElement)
            # if there is more than one same render element
            if RE_name.endswith("1"):
                cmds.delete(RE_name)

        # Set aov separator
        # First we need to explicitly set the UI items in Render Settings
        # because that is also what V-Ray updates to when that Render Settings
        # UI did initialize before and refreshes again.
        aov_separator = self.get_aov_separator()
        MENU = "vrayRenderElementSeparator"
        if cmds.optionMenuGrp(MENU, query=True, exists=True):
            items = cmds.optionMenuGrp(MENU, query=True, itemListLong=True)
            labels = [cmds.menuItem(i, query=True, label=True) for i in items]
            try:
                sep_idx = labels.index(aov_separator)
            except ValueError:
                six.reraise(
                    CreatorError,
                    CreatorError(
                        "AOV character {} not in {}".format(
                            aov_separator, labels)),
                    sys.exc_info()[2])
            else:
                cmds.optionMenuGrp(MENU, edit=True, select=sep_idx + 1)

        # Set the render element attribute as string. This is also what V-Ray
        # sets whenever the `vrayRenderElementSeparator` menu items switch
        cmds.setAttr(
            "{}.fileNameRenderElementSeparator".format(node),
            aov_separator,
            type="string"
        )

        # Set render file format to exr
        ext = vray_render_presets["image_format"]
        cmds.setAttr("{}.imageFormatStr".format(node), ext, type="string")

        # Set common > animation to "standard" to ensure frame range renders
        cmds.setAttr("{}.animType".format(node), 1)

        # resolution
        cmds.setAttr("{}.width".format(node), width)
        cmds.setAttr("{}.height".format(node), height)

        additional_options = vray_render_presets["additional_options"]
        self._additional_attribs_setter(additional_options)

    def _set_renderman_settings(self, width, height):
        """Sets settings for Renderman"""
        rman_render_presets = self["renderman_renderer"]
        aov_separator = self.get_aov_separator()

        def ensure_node_by_type(nodetype):
            """Return first existing node or create it"""
            nodes = cmds.ls(typ=nodetype)
            if len(nodes) > 0:
                return nodes[0]
            else:
                return cmds.createNode(nodetype)

        # Renderman Display filters
        display_filters = rman_render_presets["display_filters"]
        for i, display_filter in enumerate(display_filters):
            filter_node = ensure_node_by_type(display_filter)

            cmds.connectAttr(filter_node + ".message",
                             "rmanGlobals.displayFilters[%i]" % i,
                             force=True)
            if filter_node.startswith("PxrImageDisplayFilter"):
                imageDisplay_dir = self._image_dir["imageDisplay"]
                imageDisplay_dir = imageDisplay_dir.replace("{aov_separator}",
                                                            aov_separator)
                cmds.setAttr(filter_node + ".filename",
                             imageDisplay_dir, type="string")

        # Renderman sample filters
        sample_filters = rman_render_presets["sample_filters"]
        for i, sample_filter in enumerate(sample_filters):
            filter_node = ensure_node_by_type(sample_filter)

            cmds.connectAttr(filter_node + ".message",
                             "rmanGlobals.sampleFilters[%i]" % i,
                             force=True)

            if filter_node.startswith("PxrCryptomatte"):
                matte_dir = self._image_dir["cryptomatte"]
                matte_dir = matte_dir.replace("{aov_separator}",
                                              aov_separator)
                cmds.setAttr(filter_node + ".filename",
                             matte_dir, type="string")
            elif filter_node.startswith("PxrWatermarkFilter"):
                watermark_dir = self._image_dir["watermark"]
                watermark_dir = watermark_dir.replace("{aov_separator}",
                                                      aov_separator)
                cmds.setAttr(filter_node + ".filename",
                             watermark_dir, type="string")

        additional_options = rman_render_presets["additional_options"]
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

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default

    def __getitem__(self, item):
        if not isinstance(item, six.string_types):
            raise TypeError("Item must be string type")

        setting = self._project_settings["maya"]["RenderSettings"]
        try:
            for path in item.split("/"):
                setting = setting[path]
        except KeyError:
            settings_path = "project_settings/maya/RenderSettings/" + item
            raise KeyError(settings_path)

        return setting

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        return True
