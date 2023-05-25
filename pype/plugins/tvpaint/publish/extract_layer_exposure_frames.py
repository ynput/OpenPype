import pyblish.api

from avalon.tvpaint import lib, HEADLESS


class ExtractLayerExposureFrames(pyblish.api.ContextPlugin):

    order = pyblish.api.ExtractorOrder - 0.49
    label = "Extract Layer Exposure Frames"
    hosts = ["tvpaint"]

    def process(self, context):
        # Skip extract if in headless mode.
        if HEADLESS:
            return

        exposure_frames_by_layer_id = {}
        for layer in context.data["layersData"]:
            if not layer["visible"]:
                continue

            layer_id = str(layer["layer_id"])
            exposure_frames_by_layer_id[layer_id] = lib.get_exposure_frames(
                layer_id, layer["frame_start"], layer["frame_end"]
            )

        data = exposure_frames_by_layer_id
        context.data["exposure_frames_by_layer_id"] = data
        context.data["jsonData"]["exposure_frames_by_layer_id"] = data
