import os
import pyblish.api
import tde4  # noqa: F401
import threading
from openpype.pipeline import OptionalPyblishPluginMixin, publish
from openpype.hosts.equalizer.api.lib import run_warp4, convert_png, get_distortion_resolution
from openpype.hosts.equalizer.api import EqualizerHost

class ExtractWarpFootage(publish.Extractor,
                                OptionalPyblishPluginMixin):

    label = "Extract Footage Using Warp"
    families = ["warpFootage"]
    hosts = ["equalizer"]

    order = pyblish.api.ExtractorOrder - 0.01

    def process_and_convert(self, input_path, output_path):
        output = run_warp4(input_path, output_path)
        if output:
            convert_png(output)

    def process(self, instance = pyblish.api.Instance):

        if not self.is_active(instance.data):
            return
        
        cam = tde4.getCurrentCamera()
        camera_path = tde4.getCameraPath(cam)
        input_folder = os.path.dirname(camera_path)
        footage_paths = [path for path in os.listdir(input_folder) if path.endswith(".exr")][:10]
        footage_paths.sort()
        staging_dir = self.staging_dir(instance)

        threads = []
        for image in footage_paths:
            input_path = os.path.join(input_folder, image)
            output_path = os.path.join(staging_dir, image)
            thread = threading.Thread(target=self.process_and_convert, args=(input_path, output_path))
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        new_img_width, new_img_height = get_distortion_resolution(staging_dir)
        overscan_width = (new_img_width / tde4.getCameraImageWidth(cam)) * 100.0
        overscan_height = (new_img_height / tde4.getCameraImageHeight(cam)) * 100.0

        EqualizerHost.get_host().set_overscan(overscan_width, overscan_height)

        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        start, end, _ = tde4.getCameraSequenceAttr(cam)
        representation = {
            'frameStart': start,
            'frameEnd': end,
            'name': "png",
            'ext': "png",
            'files': [f for f in os.listdir(staging_dir)],
            "stagingDir": staging_dir,
        }

        self.log.debug("output: {}".format(staging_dir))
        instance.data["representations"].append(representation)
