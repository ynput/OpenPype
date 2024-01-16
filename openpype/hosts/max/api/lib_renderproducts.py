# Render Element Example : For scanline render, VRay
# https://help.autodesk.com/view/MAXDEV/2022/ENU/?guid=GUID-E8F75D47-B998-4800-A3A5-610E22913CFC
# arnold
# https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_3ds_max_ax_maxscript_commands_ax_renderview_commands_html
import os

from pymxs import runtime as rt

from openpype.hosts.max.api.lib import get_current_renderer
from openpype.pipeline import get_current_project_name
from openpype.settings import get_project_settings


class RenderProducts(object):

    def __init__(self, project_settings=None):
        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_project_settings(
                get_current_project_name()
            )

    def get_beauty(self, container):
        render_dir = os.path.dirname(rt.rendOutputFilename)

        output_file = os.path.join(render_dir, container)

        setting = self._project_settings
        img_fmt = setting["max"]["RenderSettings"]["image_format"]   # noqa

        start_frame = int(rt.rendStart)
        end_frame = int(rt.rendEnd) + 1

        return {
            "beauty": self.get_expected_beauty(
                output_file, start_frame, end_frame, img_fmt
            )
        }

    def get_multiple_beauty(self, outputs, cameras):
        beauty_output_frames = dict()
        for output, camera in zip(outputs, cameras):
            filename, ext = os.path.splitext(output)
            filename = filename.replace(".", "")
            ext = ext.replace(".", "")
            start_frame = int(rt.rendStart)
            end_frame = int(rt.rendEnd) + 1
            new_beauty = self.get_expected_beauty(
                filename, start_frame, end_frame, ext
            )
            beauty_output = ({
                f"{camera}_beauty": new_beauty
            })
            beauty_output_frames.update(beauty_output)
        return beauty_output_frames

    def get_multiple_aovs(self, outputs, cameras):
        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]
        aovs_frames = {}
        for output, camera in zip(outputs, cameras):
            filename, ext = os.path.splitext(output)
            filename = filename.replace(".", "")
            ext = ext.replace(".", "")
            start_frame = int(rt.rendStart)
            end_frame = int(rt.rendEnd) + 1

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
                        aovs_frames.update({
                            f"{camera}_{name}": self.get_expected_aovs(
                                filename, name, start_frame,
                                end_frame, ext)
                        })
            elif renderer == "Redshift_Renderer":
                render_name = self.get_render_elements_name()
                if render_name:
                    rs_aov_files = rt.Execute("renderers.current.separateAovFiles")     # noqa
                    # this doesn't work, always returns False
                    # rs_AovFiles = rt.RedShift_Renderer().separateAovFiles
                    if ext == "exr" and not rs_aov_files:
                        for name in render_name:
                            if name == "RsCryptomatte":
                                aovs_frames.update({
                                    f"{camera}_{name}": self.get_expected_aovs(
                                        filename, name, start_frame,
                                        end_frame, ext)
                                })
                    else:
                        for name in render_name:
                            aovs_frames.update({
                                f"{camera}_{name}": self.get_expected_aovs(
                                    filename, name, start_frame,
                                    end_frame, ext)
                            })
            elif renderer == "Arnold":
                render_name = self.get_arnold_product_name()
                if render_name:
                    for name in render_name:
                        aovs_frames.update({
                            f"{camera}_{name}": self.get_expected_arnold_product(   # noqa
                                filename, name, start_frame,
                                end_frame, ext)
                        })
            elif renderer in [
                "V_Ray_6_Hotfix_3",
                "V_Ray_GPU_6_Hotfix_3"
            ]:
                if ext != "exr":
                    render_name = self.get_render_elements_name()
                    if render_name:
                        for name in render_name:
                            aovs_frames.update({
                                f"{camera}_{name}": self.get_expected_aovs(
                                    filename, name, start_frame,
                                    end_frame, ext)
                            })

        return aovs_frames

    def get_aovs(self, container):
        render_dir = os.path.dirname(rt.rendOutputFilename)

        output_file = os.path.join(render_dir,
                                   container)

        setting = self._project_settings
        img_fmt = setting["max"]["RenderSettings"]["image_format"]   # noqa

        start_frame = int(rt.rendStart)
        end_frame = int(rt.rendEnd) + 1
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
                        name: self.get_expected_aovs(
                            output_file, name, start_frame,
                            end_frame, img_fmt)
                    })
        elif renderer == "Redshift_Renderer":
            render_name = self.get_render_elements_name()
            if render_name:
                rs_aov_files = rt.Execute("renderers.current.separateAovFiles")
                # this doesn't work, always returns False
                # rs_AovFiles = rt.RedShift_Renderer().separateAovFiles
                if img_fmt == "exr" and not rs_aov_files:
                    for name in render_name:
                        if name == "RsCryptomatte":
                            render_dict.update({
                                name: self.get_expected_aovs(
                                    output_file, name, start_frame,
                                    end_frame, img_fmt)
                            })
                else:
                    for name in render_name:
                        render_dict.update({
                            name: self.get_expected_aovs(
                                output_file, name, start_frame,
                                end_frame, img_fmt)
                        })

        elif renderer == "Arnold":
            render_name = self.get_arnold_product_name()
            if render_name:
                for name in render_name:
                    render_dict.update({
                        name: self.get_expected_arnold_product(
                            output_file, name, start_frame,
                            end_frame, img_fmt)
                    })
        elif renderer in [
            "V_Ray_6_Hotfix_3",
            "V_Ray_GPU_6_Hotfix_3"
        ]:
            if img_fmt != "exr":
                render_name = self.get_render_elements_name()
                if render_name:
                    for name in render_name:
                        render_dict.update({
                            name: self.get_expected_aovs(
                                output_file, name, start_frame,
                                end_frame, img_fmt)      # noqa
                        })

        return render_dict

    def get_expected_beauty(self, folder, start_frame, end_frame, fmt):
        beauty_frame_range = []
        for f in range(start_frame, end_frame):
            frame = "%04d" % f
            beauty_output = f"{folder}.{frame}.{fmt}"
            beauty_output = beauty_output.replace("\\", "/")
            beauty_frame_range.append(beauty_output)

        return beauty_frame_range

    def get_arnold_product_name(self):
        """Get all the Arnold AOVs name"""
        aov_name = []

        amw = rt.MaxToAOps.AOVsManagerWindow()
        aov_mgr = rt.renderers.current.AOVManager
        # Check if there is any aov group set in AOV manager
        aov_group_num = len(aov_mgr.drivers)
        if aov_group_num < 1:
            return
        for i in range(aov_group_num):
            # get the specific AOV group
            aov_name.extend(aov.name for aov in aov_mgr.drivers[i].aov_list)
        # close the AOVs manager window
        amw.close()

        return aov_name

    def get_expected_arnold_product(self, folder, name,
                                    start_frame, end_frame, fmt):
        """Get all the expected Arnold AOVs"""
        aov_list = []
        for f in range(start_frame, end_frame):
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

    def get_expected_aovs(self, folder, name,
                          start_frame, end_frame, fmt):
        """Get all the expected render element output files. """
        render_elements = []
        for f in range(start_frame, end_frame):
            frame = "%04d" % f
            render_element = f"{folder}_{name}.{frame}.{fmt}"
            render_element = render_element.replace("\\", "/")
            render_elements.append(render_element)

        return render_elements

    def image_format(self):
        return self._project_settings["max"]["RenderSettings"]["image_format"]  # noqa
