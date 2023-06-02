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

    def __init__(self, project_settings=None):
        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_project_settings(
                legacy_io.Session["AVALON_PROJECT"]
            )

    def render_product(self, container):
        folder = rt.maxFilePath
        file = rt.maxFileName
        folder = folder.replace("\\", "/")
        setting = self._project_settings
        render_folder = get_default_render_folder(setting)
        filename, ext = os.path.splitext(file)

        output_file = os.path.join(folder,
                                   render_folder,
                                   filename,
                                   container)

        context = get_current_project_asset()
        # TODO: change the frame range follows the current render setting
        startFrame = int(rt.rendStart)
        endFrame = int(rt.rendEnd) + 1

        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa
        full_render_list = self.beauty_render_product(output_file,
                                                      startFrame,
                                                      endFrame,
                                                      img_fmt)

        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]


        if renderer == "VUE_File_Renderer":
            return full_render_list

        if renderer in [
            "ART_Renderer",
            "Redshift_Renderer",
            "V_Ray_6_Hotfix_3",
            "V_Ray_GPU_6_Hotfix_3",
            "Default_Scanline_Renderer",
            "Quicksilver_Hardware_Renderer",
        ]:
            render_elem_list = self.render_elements_product(output_file,
                                                            startFrame,
                                                            endFrame,
                                                            img_fmt)
            if render_elem_list:
                full_render_list.extend(iter(render_elem_list))
            return full_render_list

        if renderer == "Arnold":
            aov_list = self.arnold_render_product(output_file,
                                                  startFrame,
                                                  endFrame,
                                                  img_fmt)
            if aov_list:
                full_render_list.extend(iter(aov_list))
            return full_render_list

    def beauty_render_product(self, folder, startFrame, endFrame, fmt):
        beauty_frame_range = []
        for f in range(startFrame, endFrame):
            beauty_output = f"{folder}.{f}.{fmt}"
            beauty_output = beauty_output.replace("\\", "/")
            beauty_frame_range.append(beauty_output)

        return beauty_frame_range

    # TODO: Get the arnold render product
    def arnold_render_product(self, folder, startFrame, endFrame, fmt):
        """Get all the Arnold AOVs"""
        aovs = []

        amw = rt.MaxtoAOps.AOVsManagerWindow()
        aov_mgr = rt.renderers.current.AOVManager
        # Check if there is any aov group set in AOV manager
        aov_group_num = len(aov_mgr.drivers)
        if aov_group_num < 1:
            return
        for i in range(aov_group_num):
            # get the specific AOV group
            for aov in aov_mgr.drivers[i].aov_list:
                for f in range(startFrame, endFrame):
                    render_element = f"{folder}_{aov.name}.{f}.{fmt}"
                    render_element = render_element.replace("\\", "/")
                    aovs.append(render_element)

        # close the AOVs manager window
        amw.close()

        return aovs

    def render_elements_product(self, folder, startFrame, endFrame, fmt):
        """Get all the render element output files. """
        render_dirname = []

        render_elem = rt.maxOps.GetCurRenderElementMgr()
        render_elem_num = render_elem.NumRenderElements()
        # get render elements from the renders
        for i in range(render_elem_num):
            renderlayer_name = render_elem.GetRenderElement(i)
            target, renderpass = str(renderlayer_name).split(":")
            if renderlayer_name.enabled:
                for f in range(startFrame, endFrame):
                    render_element = f"{folder}_{renderpass}.{f}.{fmt}"
                    render_element = render_element.replace("\\", "/")
                    render_dirname.append(render_element)

        return render_dirname

    def image_format(self):
        return self._project_settings["max"]["RenderSettings"]["image_format"]  # noqa
