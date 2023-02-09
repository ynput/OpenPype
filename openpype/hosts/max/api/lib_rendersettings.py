import os
from pymxs import runtime as rt
from openpype.lib import Logger
from openpype.settings import get_project_settings
from openpype.pipeline import legacy_io
from openpype.pipeline.context_tools import get_current_project_asset

from openpype.hosts.max.api.lib import (
    set_framerange,
    get_current_renderer,
    get_default_render_folder
)


class RenderSettings(object):

    log = Logger.get_logger("RenderSettings")

    _aov_chars = {
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }

    @classmethod
    def __init__(self, project_settings=None):
        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_project_settings(
                legacy_io.Session["AVALON_PROJECT"]
            )

    def set_render_camera(self, selection):
        for sel in selection:
            # to avoid Attribute Error from pymxs wrapper
            found = False
            if rt.classOf(sel) in rt.Camera.classes:
                found = True
                rt.viewport.setCamera(sel)
                break
            if not found:
                raise RuntimeError("Camera not found")

    def set_renderoutput(self, container):
        folder = rt.maxFilePath
        # hard-coded, should be customized in the setting
        folder = folder.replace("\\", "/")
        # hard-coded, set the renderoutput path
        setting = self._project_settings
        render_folder = get_default_render_folder(setting)
        output_dir = os.path.join(folder, render_folder)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # hard-coded, should be customized in the setting
        context = get_current_project_asset()

        # get project reoslution
        width = context["data"].get("resolutionWidth")
        height = context["data"].get("resolutionHeight")
        # Set Frame Range
        startFrame = context["data"].get("frameStart")
        endFrame = context["data"].get("frameEnd")
        set_framerange(startFrame, endFrame)
        # get the production render
        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]

        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa
        output = os.path.join(output_dir, container)
        try:
            aov_separator = self._aov_chars[(
                self._project_settings["maya"]
                                      ["RenderSettings"]
                                      ["aov_separator"]
            )]
        except KeyError:
            aov_separator = "."
        outputFilename = "{0}.{1}".format(output, img_fmt)
        outputFilename = outputFilename.replace("{aov_separator}",
                                                aov_separator)
        rt.rendOutputFilename = outputFilename
        if renderer == "VUE_File_Renderer":
            return
        # TODO: Finish the arnold render setup
        if renderer == "Arnold":
            return

        if (renderer == "ART_Renderer"
            or renderer == "Redshift Renderer"
            or renderer == "V_Ray_6_Hotfix_3"
            or renderer == "V_Ray_GPU_6_Hotfix_3"
            or renderer == "Default_Scanline_Renderer"
            or renderer == "Quicksilver_Hardware_Renderer"):
            self.render_element_layer(output, width, height, img_fmt)

        rt.rendSaveFile = True

    def render_element_layer(self, dir, width, height, ext):
        """For Renderers with render elements"""
        rt.renderWidth = width
        rt.renderHeight = height
        render_elem = rt.maxOps.GetCurRenderElementMgr()
        render_elem_num = render_elem.NumRenderElements()
        if render_elem_num < 0:
            return

        for i in range(render_elem_num):
            renderlayer_name = render_elem.GetRenderElement(i)
            target, renderpass = str(renderlayer_name).split(":")
            render_element = os.path.join(dir, renderpass)
            aov_name = "{0}.{1}".format(render_element, ext)
            try:
                aov_separator = self._aov_chars[(
                    self._project_settings["maya"]
                                          ["RenderSettings"]
                                          ["aov_separator"]
                )]
            except KeyError:
                aov_separator = "."

            aov_name = aov_name.replace("{aov_separator}",
                                        aov_separator)
            render_elem.SetRenderElementFileName(i, aov_name)
