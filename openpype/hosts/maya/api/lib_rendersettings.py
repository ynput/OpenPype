# -*- coding: utf-8 -*-
"""Class for handling Render Settings."""
import six
import sys

from openpype.lib import Logger
from openpype.settings import get_project_settings

from openpype.pipeline import CreatorError, get_current_project_name
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.hosts.maya.api.lib import reset_frame_range


class RenderSettings(object):

    _image_prefix_nodes = {
        'vray': 'vraySettings.fileNamePrefix',
        'arnold': 'defaultRenderGlobals.imageFilePrefix',
        'renderman': 'rmanGlobals.imageFileFormat',
        'redshift': 'defaultRenderGlobals.imageFilePrefix',
        'mayahardware2': 'defaultRenderGlobals.imageFilePrefix'
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

    @staticmethod
    def get_padding_attr(renderer):
        """Return attribute for renderer that defines frame padding amount"""
        if renderer == "vray":
            return "vraySettings.fileNamePadding"
        else:
            return "defaultRenderGlobals.extensionPadding"

    def __init__(self, project_settings=None):
        if not project_settings:
            project_settings = get_project_settings(
                get_current_project_name()
            )
        render_settings = project_settings["maya"]["RenderSettings"]
        image_prefixes = {
            "vray": render_settings["vray_renderer"]["image_prefix"],
            "arnold": render_settings["arnold_renderer"]["image_prefix"],
            "renderman": render_settings["renderman_renderer"]["image_prefix"],
            "redshift": render_settings["redshift_renderer"]["image_prefix"]
        }

        # TODO probably should be stored to more explicit attribute
        # Renderman only
        renderman_settings = render_settings["renderman_renderer"]
        _image_dir = {
            "renderman": renderman_settings["image_dir"],
            "cryptomatte": renderman_settings["cryptomatte_dir"],
            "imageDisplay": renderman_settings["imageDisplay_dir"],
            "watermark": renderman_settings["watermark_dir"]
        }
        self._image_prefixes = image_prefixes
        self._image_dir = _image_dir
        self._project_settings = project_settings

    def set_default_renderer_settings(self, renderer=None):
        """Set basic settings based on renderer."""
        # Not all hosts can import this module.
        from maya import cmds  # noqa: F401
        import maya.mel as mel  # noqa: F401

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
        reset_frame = self._project_settings["maya"]["RenderSettings"]["reset_current_frame"] # noqa

        if reset_frame:
            start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
            cmds.currentTime(start_frame, edit=True)

        if renderer in self._image_prefix_nodes:
            prefix = self._image_prefixes[renderer]
            prefix = prefix.replace("{aov_separator}", aov_separator)
            cmds.setAttr(self._image_prefix_nodes[renderer],
                        prefix, type="string")  # noqa
        else:
            print("{0} isn't a supported renderer to autoset settings.".format(renderer)) # noqa
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
            mel.eval("redshiftUpdateActiveAovList")

        if renderer == "renderman":
            image_dir = self._image_dir["renderman"]
            cmds.setAttr("rmanGlobals.imageOutputDir",
                         image_dir, type="string")
            self._set_renderman_settings(width, height,
                                         aov_separator)

    def _set_arnold_settings(self, width, height):
        """Sets settings for Arnold."""
        from mtoa.core import createOptions  # noqa
        from mtoa.aovs import AOVInterface  # noqa
        # Not all hosts can import this module.
        from maya import cmds  # noqa: F401
        import maya.mel as mel  # noqa: F401

        createOptions()
        render_settings = self._project_settings["maya"]["RenderSettings"]
        arnold_render_presets = render_settings["arnold_renderer"] # noqa
        # Force resetting settings and AOV list to avoid having to deal with
        # AOV checking logic, for now.
        # This is a work around because the standard
        # function to revert render settings does not reset AOVs list in MtoA
        # Fetch current aovs in case there's any.
        current_aovs = AOVInterface().getAOVs()
        remove_aovs = render_settings["remove_aovs"]
        if remove_aovs:
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
            if aov in current_aovs and not remove_aovs:
                continue
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
        reset_frame_range(playback=False, fps=False, render=True)

    def _set_redshift_settings(self, width, height):
        """Sets settings for Redshift."""
        # Not all hosts can import this module.
        from maya import cmds  # noqa: F401
        import maya.mel as mel  # noqa: F401

        render_settings = self._project_settings["maya"]["RenderSettings"]
        redshift_render_presets = render_settings["redshift_renderer"]

        remove_aovs = render_settings["remove_aovs"]
        all_rs_aovs = cmds.ls(type='RedshiftAOV')
        if remove_aovs:
            for aov in all_rs_aovs:
                enabled = cmds.getAttr("{}.enabled".format(aov))
                if enabled:
                    cmds.delete(aov)

        redshift_aovs = redshift_render_presets["aov_list"]
        # list all the aovs
        all_rs_aovs = cmds.ls(type='RedshiftAOV')
        for rs_aov in redshift_aovs:
            rs_layername = "rsAov_{}".format(rs_aov.replace(" ", ""))
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

        additional_options = redshift_render_presets["additional_options"]
        ext = redshift_render_presets["image_format"]
        img_exts = ["iff", "exr", "tif", "png", "tga", "jpg"]
        img_ext = img_exts.index(ext)

        self._set_global_output_settings()
        cmds.setAttr("redshiftOptions.imageFormat", img_ext)
        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)
        self._additional_attribs_setter(additional_options)

    def _set_renderman_settings(self, width, height, aov_separator):
        """Sets settings for Renderman"""
        # Not all hosts can import this module.
        from maya import cmds  # noqa: F401
        import maya.mel as mel  # noqa: F401

        rman_render_presets = (
            self._project_settings
            ["maya"]
            ["RenderSettings"]
            ["renderman_renderer"]
        )
        display_filters = rman_render_presets["display_filters"]
        d_filters_number = len(display_filters)
        for i in range(d_filters_number):
            d_node = cmds.ls(typ=display_filters[i])
            if len(d_node) > 0:
                filter_nodes = d_node[0]
            else:
                filter_nodes = cmds.createNode(display_filters[i])

            cmds.connectAttr(filter_nodes + ".message",
                             "rmanGlobals.displayFilters[%i]" % i,
                             force=True)
            if filter_nodes.startswith("PxrImageDisplayFilter"):
                imageDisplay_dir = self._image_dir["imageDisplay"]
                imageDisplay_dir = imageDisplay_dir.replace("{aov_separator}",
                                                            aov_separator)
                cmds.setAttr(filter_nodes + ".filename",
                             imageDisplay_dir, type="string")

        sample_filters = rman_render_presets["sample_filters"]
        s_filters_number = len(sample_filters)
        for n in range(s_filters_number):
            s_node = cmds.ls(typ=sample_filters[n])
            if len(s_node) > 0:
                filter_nodes = s_node[0]
            else:
                filter_nodes = cmds.createNode(sample_filters[n])

            cmds.connectAttr(filter_nodes + ".message",
                             "rmanGlobals.sampleFilters[%i]" % n,
                             force=True)

            if filter_nodes.startswith("PxrCryptomatte"):
                matte_dir = self._image_dir["cryptomatte"]
                matte_dir = matte_dir.replace("{aov_separator}",
                                              aov_separator)
                cmds.setAttr(filter_nodes + ".filename",
                             matte_dir, type="string")
            elif filter_nodes.startswith("PxrWatermarkFilter"):
                watermark_dir = self._image_dir["watermark"]
                watermark_dir = watermark_dir.replace("{aov_separator}",
                                                      aov_separator)
                cmds.setAttr(filter_nodes + ".filename",
                             watermark_dir, type="string")

        additional_options = rman_render_presets["additional_options"]

        self._set_global_output_settings()
        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)
        self._additional_attribs_setter(additional_options)

    def _set_vray_settings(self, aov_separator, width, height):
        # type: (str, int, int) -> None
        """Sets important settings for Vray."""
        # Not all hosts can import this module.
        from maya import cmds  # noqa: F401
        import maya.mel as mel  # noqa: F401


        settings = cmds.ls(type="VRaySettingsNode")
        node = settings[0] if settings else cmds.createNode("VRaySettingsNode")
        render_settings = self._project_settings["maya"]["RenderSettings"]
        vray_render_presets = render_settings["vray_renderer"]
        # vrayRenderElement
        remove_aovs = render_settings["remove_aovs"]
        all_vray_aovs = cmds.ls(type='VRayRenderElement')
        lightSelect_aovs = cmds.ls(type='VRayRenderElementSet')
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
        MENU = "vrayRenderElementSeparator"
        if cmds.optionMenuGrp(MENU, query=True, exists=True):
            items = cmds.optionMenuGrp(MENU, query=True, ill=True)
            separators = [cmds.menuItem(i, query=True, label=True) for i in items]  # noqa: E501
            try:
                sep_idx = separators.index(aov_separator)
            except ValueError:
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
        ext = vray_render_presets["image_format"]
        cmds.setAttr("{}.imageFormatStr".format(node), ext, type="string")

        # animType
        cmds.setAttr("{}.animType".format(node), 1)

        # resolution
        cmds.setAttr("{}.width".format(node), width)
        cmds.setAttr("{}.height".format(node), height)

        additional_options = vray_render_presets["additional_options"]

        self._additional_attribs_setter(additional_options)

    @staticmethod
    def _set_global_output_settings():
        # Not all hosts can import this module.
        from maya import cmds  # noqa: F401
        import maya.mel as mel  # noqa: F401

        # enable animation
        cmds.setAttr("defaultRenderGlobals.outFormatControl", 0)
        cmds.setAttr("defaultRenderGlobals.animation", 1)
        cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", 1)
        cmds.setAttr("defaultRenderGlobals.extensionPadding", 4)

    def _additional_attribs_setter(self, additional_attribs):
        # Not all hosts can import this module.
        from maya import cmds  # noqa: F401
        import maya.mel as mel  # noqa: F401

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
