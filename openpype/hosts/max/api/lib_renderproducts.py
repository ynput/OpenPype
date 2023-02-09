# Render Element Example : For scanline render, VRay
# https://help.autodesk.com/view/MAXDEV/2022/ENU/?guid=GUID-E8F75D47-B998-4800-A3A5-610E22913CFC
# arnold
# https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_3ds_max_ax_maxscript_commands_ax_renderview_commands_html
import os
from pymxs import runtime as rt
from openpype.hosts.max.api.lib import (
    get_current_renderer,
    get_default_render_folder
)
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.settings import get_project_settings
from openpype.pipeline import legacy_io


class RenderProducts(object):

    @classmethod
    def __init__(self, project_settings=None):
        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_project_settings(
                legacy_io.Session["AVALON_PROJECT"]
            )

    def render_product(self, container):
        folder = rt.maxFilePath
        folder = folder.replace("\\", "/")
        setting = self._project_settings
        render_folder = get_default_render_folder(setting)

        output_file = os.path.join(folder, render_folder, container)
        context = get_current_project_asset()
        startFrame = context["data"].get("frameStart")
        endFrame = context["data"].get("frameEnd") + 1

        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa
        full_render_list = self.beauty_render_product(output_file,
                                                      startFrame,
                                                      endFrame,
                                                      img_fmt)
        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]

        if renderer == "VUE_File_Renderer":
            return full_render_list

        if (
            renderer == "ART_Renderer" or
            renderer == "Redshift Renderer" or
            renderer == "V_Ray_6_Hotfix_3" or
            renderer == "V_Ray_GPU_6_Hotfix_3" or
            renderer == "Default_Scanline_Renderer" or
            renderer == "Quicksilver_Hardware_Renderer"
        ):
            render_elem_list = self.render_elements_product(output_file,
                                                            startFrame,
                                                            endFrame,
                                                            img_fmt)
            for render_elem in render_elem_list:
                full_render_list.append(render_elem)
            return full_render_list

        if renderer == "Arnold":
            return full_render_list

    def beauty_render_product(self, folder, startFrame, endFrame, fmt):
        # get the beauty
        beauty_frame_range = list()

        for f in range(startFrame, endFrame):
            beauty = "{0}.{1}.{2}".format(folder,
                                          str(f),
                                          fmt)
            beauty = beauty.replace("\\", "/")
            beauty_frame_range.append(beauty)

        return beauty_frame_range

    # TODO: Get the arnold render product
    def render_elements_product(self, folder, startFrame, endFrame, fmt):
        """Get all the render element output files. """
        render_dirname = list()

        render_elem = rt.maxOps.GetCurRenderElementMgr()
        render_elem_num = render_elem.NumRenderElements()
        # get render elements from the renders
        for i in range(render_elem_num):
            renderlayer_name = render_elem.GetRenderElement(i)
            target, renderpass = str(renderlayer_name).split(":")

            render_dir = os.path.join(folder, renderpass)
            if renderlayer_name.enabled:
                for f in range(startFrame, endFrame):
                    render_element = "{0}.{1}.{2}".format(render_dir,
                                                          str(f),
                                                          fmt)
                    render_element = render_element.replace("\\", "/")
                    render_dirname.append(render_element)

        return render_dirname

    def image_format(self):
        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa
        return img_fmt
