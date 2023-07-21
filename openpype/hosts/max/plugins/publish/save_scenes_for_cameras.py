import pyblish.api
import os
import sys
import tempfile

from pymxs import runtime as rt
from openpype.lib import run_subprocess
from openpype.hosts.max.api.lib import get_max_version
from openpype.hosts.max.api.lib_rendersettings import RenderSettings
from openpype.hosts.max.api.lib_renderproducts import RenderProducts


class SaveScenesForCamera(pyblish.api.InstancePlugin):
    """Save scene files for multiple cameras without
    editing the original scene before deadline submission

    """

    label = "Save Scene files for cameras"
    order = pyblish.api.ExtractorOrder - 0.48
    hosts = ["max"]
    families = ["maxrender", "workfile"]

    def process(self, instance):
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
        new_folder = "{}_{}".format(current_folder, filename)
        os.makedirs(new_folder, exist_ok=True)
        for camera in cameras:
            new_output = RenderSettings().get_batch_render_output(camera)       # noqa
            new_output = new_output.replace("\\", "/")
            new_filename = "{}_{}{}".format(
                filename, camera, ext)
            new_filepath = os.path.join(new_folder, new_filename)
            new_filepath = new_filepath.replace("\\", "/")
            camera_scene_files.append(new_filepath)
            RenderSettings().batch_render_elements(camera)
            rt.rendOutputFilename = new_output
            rt.saveMaxFile(current_filepath)
            script = ("""
from pymxs import runtime as rt
import os
new_filepath = "{new_filepath}"
new_output = "{new_output}"
camera = "{camera}"
rt.rendOutputFilename = new_output
directory = os.path.dirname(new_output)
render_elem = rt.maxOps.GetCurRenderElementMgr()
render_elem_num = render_elem.NumRenderElements()
if render_elem_num > 0:
    ext = "{ext}"
    for i in range(render_elem_num):
        renderlayer_name = render_elem.GetRenderElement(i)
        target, renderpass = str(renderlayer_name).split(":")
        aov_name = directory + "_" + camera + "_" + renderpass + "." + "." + ext        # noqa
        render_elem.SetRenderElementFileName(i, aov_name)
rt.saveMaxFile(new_filepath)
        """).format(new_filepath=new_filepath,
                    new_output=new_output,
                    camera=camera,
                    ext=fmt)
            scripts.append(script)

        max_version = get_max_version()
        maxBatch_exe = os.path.join(
            os.getenv(f"ADSK_3DSMAX_x64_{max_version}"), "3dsmaxbatch")
        maxBatch_exe = maxBatch_exe.replace("\\", "/")
        if sys.platform == "windows":
            maxBatch_exe += ".exe"
            maxBatch_exe = os.path.normpath(maxBatch_exe)
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
                run_subprocess([maxBatch_exe, tmp_script_path,
                                "-sceneFile", current_filepath])
            except RuntimeError:
                self.log.debug("Checking the scene files existing")

        for camera_scene, camera in zip(camera_scene_files, cameras):
            if not os.path.exists(camera_scene):
                self.log.error("Camera scene files not existed yet!")
                raise RuntimeError("MaxBatch.exe doesn't run as expected")
            self.log.debug(f"Found Camera scene:{camera_scene}")

        if "sceneFiles" not in instance.data:
            instance.data["sceneFiles"] = camera_scene_files
