import os
from pymxs import runtime as rt
from openpype.lib import Logger
from openpype.settings import get_project_settings
from openpype.pipeline import get_current_project_name
from openpype.pipeline.context_tools import get_current_project_asset

from openpype.hosts.max.api.lib import (
    set_render_frame_range,
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

    def __init__(self, project_settings=None):
        """
        Set up the naming convention for the render
        elements for the deadline submission
        """

        self._project_settings = project_settings
        if not self._project_settings:
            self._project_settings = get_project_settings(
                get_current_project_name()
            )

    def set_render_camera(self, selection):
        for sel in selection:
            # to avoid Attribute Error from pymxs wrapper
            if rt.classOf(sel) in rt.Camera.classes:
                rt.viewport.setCamera(sel)
                return
        raise RuntimeError("Active Camera not found")

    def render_output(self, container):
        folder = rt.maxFilePath
        # hard-coded, should be customized in the setting
        file = rt.maxFileName
        folder = folder.replace("\\", "/")
        # hard-coded, set the renderoutput path
        setting = self._project_settings
        render_folder = get_default_render_folder(setting)
        filename, ext = os.path.splitext(file)
        output_dir = os.path.join(folder,
                                  render_folder,
                                  filename)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # hard-coded, should be customized in the setting
        context = get_current_project_asset()

        # get project resolution
        width = context["data"].get("resolutionWidth")
        height = context["data"].get("resolutionHeight")
        # Set Frame Range
        frame_start = context["data"].get("frame_start")
        frame_end = context["data"].get("frame_end")
        set_render_frame_range(frame_start, frame_end)
        # get the production render
        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]

        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa
        output = os.path.join(output_dir, container)
        try:
            aov_separator = self._aov_chars[(
                self._project_settings["max"]
                                      ["RenderSettings"]
                                      ["aov_separator"]
            )]
        except KeyError:
            aov_separator = "."
        output_filename = f"{output}..{img_fmt}"
        output_filename = output_filename.replace("{aov_separator}",
                                                  aov_separator)
        rt.rendOutputFilename = output_filename
        if renderer == "VUE_File_Renderer":
            return
        # TODO: Finish the arnold render setup
        if renderer == "Arnold":
            self.arnold_setup()

        if renderer in [
            "ART_Renderer",
            "Redshift_Renderer",
            "V_Ray_6_Hotfix_3",
            "V_Ray_GPU_6_Hotfix_3",
            "Default_Scanline_Renderer",
            "Quicksilver_Hardware_Renderer",
        ]:
            self.render_element_layer(output, width, height, img_fmt)

        rt.rendSaveFile = True

        if rt.renderSceneDialog.isOpen():
            rt.renderSceneDialog.close()

    def arnold_setup(self):
        # get Arnold RenderView run in the background
        # for setting up renderable camera
        arv = rt.MAXToAOps.ArnoldRenderView()
        render_camera = rt.viewport.GetCamera()
        if render_camera:
            arv.setOption("Camera", str(render_camera))

        # TODO: add AOVs and extension
        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa
        setup_cmd = (
            f"""
        amw = MaxtoAOps.AOVsManagerWindow()
        amw.close()
        aovmgr = renderers.current.AOVManager
        aovmgr.drivers = #()
        img_fmt = "{img_fmt}"
        if img_fmt == "png" then driver = ArnoldPNGDriver()
        if img_fmt == "jpg" then driver = ArnoldJPEGDriver()
        if img_fmt == "exr" then driver = ArnoldEXRDriver()
        if img_fmt == "tif" then driver = ArnoldTIFFDriver()
        if img_fmt == "tiff" then driver = ArnoldTIFFDriver()
        append aovmgr.drivers driver
        aovmgr.drivers[1].aov_list = #()
            """)

        rt.execute(setup_cmd)
        arv.close()

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
            aov_name = f"{dir}_{renderpass}..{ext}"
            render_elem.SetRenderElementFileName(i, aov_name)

    def get_render_output(self, container, output_dir):
        output = os.path.join(output_dir, container)
        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa
        output_filename = f"{output}..{img_fmt}"
        return output_filename

    def get_render_element(self):
        orig_render_elem = []
        render_elem = rt.maxOps.GetCurRenderElementMgr()
        render_elem_num = render_elem.NumRenderElements()
        if render_elem_num < 0:
            return

        for i in range(render_elem_num):
            render_element = render_elem.GetRenderElementFilename(i)
            orig_render_elem.append(render_element)

        return orig_render_elem

    def get_batch_render_elements(self, container,
                                  output_dir, camera):
        render_element_list = list()
        output = os.path.join(output_dir, container)
        render_elem = rt.maxOps.GetCurRenderElementMgr()
        render_elem_num = render_elem.NumRenderElements()
        if render_elem_num < 0:
            return
        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa

        for i in range(render_elem_num):
            renderlayer_name = render_elem.GetRenderElement(i)
            target, renderpass = str(renderlayer_name).split(":")
            aov_name = f"{output}_{camera}_{renderpass}..{img_fmt}"
            render_element_list.append(aov_name)
        return render_element_list

    def get_batch_render_output(self, camera):
        target_layer_no = rt.batchRenderMgr.FindView(camera)
        target_layer = rt.batchRenderMgr.GetView(target_layer_no)
        return target_layer.outputFilename

    def batch_render_elements(self, camera):
        target_layer_no = rt.batchRenderMgr.FindView(camera)
        target_layer = rt.batchRenderMgr.GetView(target_layer_no)
        outputfilename = target_layer.outputFilename
        directory = os.path.dirname(outputfilename)
        render_elem = rt.maxOps.GetCurRenderElementMgr()
        render_elem_num = render_elem.NumRenderElements()
        if render_elem_num < 0:
            return
        ext = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa

        for i in range(render_elem_num):
            renderlayer_name = render_elem.GetRenderElement(i)
            target, renderpass = str(renderlayer_name).split(":")
            aov_name = f"{directory}_{camera}_{renderpass}..{ext}"
            render_elem.SetRenderElementFileName(i, aov_name)

    def batch_render_layer(self, container,
                           output_dir, cameras):
        outputs = list()
        output = os.path.join(output_dir, container)
        img_fmt = self._project_settings["max"]["RenderSettings"]["image_format"]   # noqa
        for cam in cameras:
            camera = rt.getNodeByName(cam)
            layer_no = rt.batchRenderMgr.FindView(cam)
            renderlayer = None
            if layer_no == 0:
                renderlayer = rt.batchRenderMgr.CreateView(camera)
            else:
                renderlayer = rt.batchRenderMgr.GetView(layer_no)
            # use camera name as renderlayer name
            renderlayer.name = cam
            renderlayer.outputFilename = f"{output}_{cam}..{img_fmt}"
            outputs.append(renderlayer.outputFilename)
        return outputs
