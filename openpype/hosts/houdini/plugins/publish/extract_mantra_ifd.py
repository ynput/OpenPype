import os

import pyblish.api

from openpype.pipeline import publish

import hou


class ExtractMantraIFD(publish.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Mantra ifd"
    hosts = ["houdini"]
    families = ["mantraifd"]
    targets = ["local", "remote"]

    def process(self, instance):
        if instance.data.get("farm"):
            self.log.debug("Should be processed on farm, skipping.")
            return

        ropnode = hou.node(instance.data.get("instance_node"))
        output = ropnode.evalParm("soho_diskfile")
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir

        files = instance.data["frames"]
        missing_frames = [
            frame
            for frame in instance.data["frames"]
            if not os.path.exists(
                os.path.normpath(os.path.join(staging_dir, frame)))
        ]
        if missing_frames:
            raise RuntimeError("Failed to complete Mantra ifd extraction. "
                               "Missing output files: {}".format(
                                   missing_frames))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'ifd',
            'ext': 'ifd',
            'files': files,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
        }
        instance.data["representations"].append(representation)
