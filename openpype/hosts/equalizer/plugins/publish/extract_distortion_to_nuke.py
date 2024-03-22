import os
import pyblish.api
import tde4  # noqa: F401
from mock import patch
from openpype.lib import import_filepath
from openpype.pipeline import OptionalPyblishPluginMixin, publish


class ExtractDistortionToNuke(publish.Extractor,
                                OptionalPyblishPluginMixin):
    """Extract Nuke script for matchmove.

    Unfortunately built-in export script from 3DEqualizer is bound to its UI,
    and it is not possible to call it directly from Python. Because of that,
    we are executing the script in the same way as artist would do it, but
    we are patching the UI to silence it and to avoid any user interaction.

    TODO: Utilize attributes defined in ExtractScriptBase
    """

    label = "Extract Distortion To Nuke Grid Warp"
    families = ["lensDistortion"]
    hosts = ["equalizer"]

    order = pyblish.api.ExtractorOrder

    def process(self, instance = pyblish.api.Instance):

        if not self.is_active(instance.data):
            return

        camera_id = tde4.getCurrentCamera()
        lens_id = tde4.getCameraLens(camera_id)
        img_width = int(tde4.getCameraImageWidth(camera_id))
        img_height = int(tde4.getCameraImageHeight(camera_id))
        grid_width, grid_height = 10, 10
        startframe = tde4.getCameraFrameOffset(camera_id)
        img_overscan_width, img_overscan_height = img_width, img_height
        overscan = False
        flop = False

        staging_dir = self.staging_dir(instance)
        file_path = os.path.join(staging_dir, "nuke_ld_export_warp.nk")

        # import export script from 3DEqualizer
        exporter_path = os.path.join(instance.data["tde4_path"], "sys_data", "py_scripts", "export_nuke_grid_warp_generic_LD.py")  # noqa: E501
        self.log.debug("Importing {}".format(exporter_path))
        
        # Hide UI with patchin postCustomRequester
        with patch("tde4.postCustomRequester", lambda *args, **kwargs: 0),\
             patch("tde4.postProgressRequesterAndContinue", lambda *args, **kwargs: None),\
             patch("tde4.updateProgressRequester", lambda *args, **kwargs: True):   
            exporter = import_filepath(exporter_path)
            exporter._export_nuke_grid_warp(file_path, img_width, img_height, grid_width, grid_height, startframe, overscan, img_overscan_width, img_overscan_height, flop)

        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': "nuke_ld_export_warp",
            'ext': "warp.nk",
            'files': os.path.basename(file_path),
            "stagingDir": staging_dir,
        }
        self.log.debug("output: {}".format(file_path))
        instance.data["representations"].append(representation)
