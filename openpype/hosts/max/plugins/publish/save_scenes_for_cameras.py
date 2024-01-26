import pyblish.api
import os
import sys
import tempfile

from pymxs import runtime as rt
from openpype.lib import run_subprocess
from openpype.hosts.max.api.lib_rendersettings import RenderSettings
from openpype.hosts.max.api.lib_renderproducts import RenderProducts


class SaveScenesForCamera(pyblish.api.InstancePlugin):
    """Save scene files for multiple cameras without
    editing the original scene before deadline submission

    """

    label = "Save Scene files for cameras"
    order = pyblish.api.ExtractorOrder - 0.48
    hosts = ["max"]
    families = ["maxrender"]

    def process(self, instance):
        if not instance.data.get("multiCamera"):
            self.log.debug(
                "Multi Camera disabled. "
                "Skipping to save scene files for cameras")
            return
        current_folder = rt.maxFilePath
        current_filename = rt.maxFileName
        current_filepath = os.path.join(current_folder, current_filename)
        camera_scene_files = []
        scripts = []
        filename, ext = os.path.splitext(current_filename)
        fmt = RenderProducts().image_format()
        cameras = instance.data.get("cameras")
        if not cameras:
            return
        new_folder = f"{current_folder}_{filename}"
        os.makedirs(new_folder, exist_ok=True)
        for camera in cameras:
            new_output = RenderSettings().get_batch_render_output(camera)       # noqa
            new_output = new_output.replace("\\", "/")
            new_filename = f"{filename}_{camera}{ext}"
            new_filepath = os.path.join(new_folder, new_filename)
            new_filepath = new_filepath.replace("\\", "/")
            camera_scene_files.append(new_filepath)
            RenderSettings().batch_render_elements(camera)
            rt.rendOutputFilename = new_output
            rt.saveMaxFile(current_filepath)
            script = ("""
from pymxs import runtime as rt
import os
filename = "{filename}"
new_filepath = "{new_filepath}"
new_output = "{new_output}"
camera = "{camera}"
rt.rendOutputFilename = new_output
directory = os.path.dirname(rt.rendOutputFilename)
directory = os.path.join(directory, filename)
render_elem = rt.maxOps.GetCurRenderElementMgr()
render_elem_num = render_elem.NumRenderElements()
if render_elem_num > 0:
    ext = "{ext}"
    for i in range(render_elem_num):
        renderlayer_name = render_elem.GetRenderElement(i)
        target, renderpass = str(renderlayer_name).split(":")
        aov_name =  f"{{directory}}_{camera}_{{renderpass}}..{ext}"
        render_elem.SetRenderElementFileName(i, aov_name)
rt.saveMaxFile(new_filepath)
        """).format(filename=instance.name,
                    new_filepath=new_filepath,
                    new_output=new_output,
                    camera=camera,
                    ext=fmt)
            scripts.append(script)

        maxbatch_exe = os.path.join(
            os.path.dirname(sys.executable), "3dsmaxbatch")
        maxbatch_exe = maxbatch_exe.replace("\\", "/")
        if sys.platform == "windows":
            maxbatch_exe += ".exe"
            maxbatch_exe = os.path.normpath(maxbatch_exe)
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_script_path = os.path.join(
                tmp_dir_name, "extract_scene_files.py")
            self.log.info("Using script file: {}".format(tmp_script_path))

            with open(tmp_script_path, "wt") as tmp:
                for script in scripts:
                    tmp.write(script + "\n")

            try:
                current_filepath = current_filepath.replace("\\", "/")
                tmp_script_path = tmp_script_path.replace("\\", "/")
                run_subprocess([maxbatch_exe, tmp_script_path,
                                "-sceneFile", current_filepath])
            except RuntimeError:
                self.log.debug("Checking the scene files existing")

        for camera_scene in camera_scene_files:
            if not os.path.exists(camera_scene):
                self.log.error("Camera scene files not existed yet!")
                raise RuntimeError("MaxBatch.exe doesn't run as expected")
            self.log.debug(f"Found Camera scene:{camera_scene}")
