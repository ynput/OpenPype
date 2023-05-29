# Render Element Example : For scanline render, VRay
# https://help.autodesk.com/view/MAXDEV/2022/ENU/?guid=GUID-E8F75D47-B998-4800-A3A5-610E22913CFC
# arnold
# https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_3ds_max_ax_maxscript_commands_ax_renderview_commands_html
import os
from pymxs import runtime as rt
from openpype.hosts.max.api.lib import (
    get_current_renderer
)
from openpype.settings import get_project_settings
from openpype.pipeline import legacy_io


class RenderProducts(object):

    def __init__(self, project_settings=None):
        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_project_settings(
                legacy_io.Session["AVALON_PROJECT"]
            )

    def get_beauty(self, container):
        render_dir = os.path.dirname(rt.rendOutputFilename)

        output_file = os.path.join(render_dir,
                                   container)

        setting = self._project_settings
        img_fmt = setting["max"]["RenderSettings"]["image_format"]   # noqa

        startFrame = int(rt.rendStart)
        endFrame = int(rt.rendEnd) + 1

        render_dict = {
            "beauty": self.get_expected_beauty(
                output_file, startFrame, endFrame, img_fmt)
        }
        return render_dict

    def get_aovs(self, container):
        render_dir = os.path.dirname(rt.rendOutputFilename)

        output_file = os.path.join(render_dir,
                                   container)

        setting = self._project_settings
        img_fmt = setting["max"]["RenderSettings"]["image_format"]   # noqa

        startFrame = int(rt.rendStart)
        endFrame = int(rt.rendEnd) + 1
        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]
        render_dict = {}

        if renderer in [
            "ART_Renderer",
            "V_Ray_6_Hotfix_3",
            "V_Ray_GPU_6_Hotfix_3",
            "Default_Scanline_Renderer",
            "Quicksilver_Hardware_Renderer",
        ]:
            render_name = self.get_render_elements_name()
            if render_name:
                for name in render_name:
                    render_dict.update({
                        name: self.get_expected_render_elements(
                            output_file, name, startFrame,
                            endFrame, img_fmt)
                    })
        if renderer == "Redshift_Renderer":
            render_name = self.get_render_elements_name()
            if render_name:
                rs_AovFiles = rt.Redshift_Renderer().SeparateAovFiles
                if rs_AovFiles == False and img_fmt == "exr":
                    for name in render_name:
                        if name == "RsCryptomatte":
                            render_dict.update({
                            name: self.get_expected_render_elements(
                                output_file, name, startFrame,
                                endFrame, img_fmt)
                        })
                else:
                    for name in render_name:
                        render_dict.update({
                            name: self.get_expected_render_elements(
                                output_file, name, startFrame,
                                endFrame, img_fmt)
                        })

        if renderer == "Arnold":
            render_name = self.get_arnold_product_name()
            if render_name:
                for name in render_name:
                    render_dict.update({
                        name: self.get_expected_arnold_product(
                            output_file, name, startFrame, endFrame, img_fmt)
                    })
        if renderer in [
            "V_Ray_6_Hotfix_3",
            "V_Ray_GPU_6_Hotfix_3"
            ]:
            if img_fmt !="exr":
                render_name = self.get_render_elements_name()
                if render_name:
                    for name in render_name:
                        render_dict.update({
                            name: self.get_expected_render_elements(
                                output_file, name, startFrame,
                                endFrame, img_fmt)      # noqa
                        })

        return render_dict

    def get_expected_beauty(self, folder, startFrame, endFrame, fmt):
        beauty_frame_range = []
        for f in range(startFrame, endFrame):
            frame = "%04d" % f
            beauty_output = f"{folder}.{frame}.{fmt}"
            beauty_output = beauty_output.replace("\\", "/")
            beauty_frame_range.append(beauty_output)

        return beauty_frame_range

    def get_arnold_product_name(self):
        """Get all the Arnold AOVs name"""
        aov_name = []

        amw = rt.MaxtoAOps.AOVsManagerWindow()
        aov_mgr = rt.renderers.current.AOVManager
        # Check if there is any aov group set in AOV manager
        aov_group_num = len(aov_mgr.drivers)
        if aov_group_num < 1:
            return
        for i in range(aov_group_num):
            # get the specific AOV group
            for aov in aov_mgr.drivers[i].aov_list:
                aov_name.append(aov.name)

        # close the AOVs manager window
        amw.close()

        return aov_name

    def get_expected_arnold_product(self, folder, name,
                                    startFrame, endFrame, fmt):
        """Get all the expected Arnold AOVs"""
        aov_list = []
        for f in range(startFrame, endFrame):
            frame = "%04d" % f
            render_element = f"{folder}_{name}.{frame}.{fmt}"
            render_element = render_element.replace("\\", "/")
            aov_list.append(render_element)

        return aov_list

    def get_render_elements_name(self):
        """Get all the render element names for general """
        render_name = []
        render_elem = rt.maxOps.GetCurRenderElementMgr()
        render_elem_num = render_elem.NumRenderElements()
        if render_elem_num < 1:
            return
        # get render elements from the renders
        for i in range(render_elem_num):
            renderlayer_name = render_elem.GetRenderElement(i)
            if renderlayer_name.enabled:
                target, renderpass = str(renderlayer_name).split(":")
                render_name.append(renderpass)

        return render_name

    def get_expected_render_elements(self, folder, name,
                                     startFrame, endFrame, fmt):
        """Get all the expected render element output files. """
        render_elements = []
        for f in range(startFrame, endFrame):
            frame = "%04d" % f
            render_element = f"{folder}_{name}.{frame}.{fmt}"
            render_element = render_element.replace("\\", "/")
            render_elements.append(render_element)

        return render_elements

    def image_format(self):
        return self._project_settings["max"]["RenderSettings"]["image_format"]  # noqa
