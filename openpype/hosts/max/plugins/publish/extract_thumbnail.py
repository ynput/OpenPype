import os
import tempfile
import pyblish.api
from pymxs import runtime as rt
from openpype.pipeline import publish
from openpype.hosts.max.api.lib import (
    viewport_setup_updated,
    viewport_setup,
    get_max_version,
    set_preview_arg
)



class ExtractThumbnail(publish.Extractor):
    """
    Extract Thumbnail for Review
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Thumbnail"
    hosts = ["max"]
    families = ["review"]

    def process(self, instance):
        # TODO: Create temp directory for thumbnail
        # - this is to avoid "override" of source file
        tmp_staging = tempfile.mkdtemp(prefix="pyblish_tmp_")
        self.log.debug(
            f"Create temp directory {tmp_staging} for thumbnail"
        )
        fps = float(instance.data["fps"])
        frame = int(instance.data["frameStart"])
        instance.context.data["cleanupFullPaths"].append(tmp_staging)
        filename = "{name}_thumbnail..png".format(**instance.data)
        filepath = os.path.join(tmp_staging, filename)
        filepath = filepath.replace("\\", "/")
        thumbnail = self.get_filename(instance.name, frame)

        self.log.debug(
            "Writing Thumbnail to"
            " '%s' to '%s'" % (filename, tmp_staging))
        review_camera = instance.data["review_camera"]
        if get_max_version() >= 2024:
            with viewport_setup_updated(review_camera):
                preview_arg = set_preview_arg(
                    instance, filepath, frame, frame, fps)
                rt.execute(preview_arg)
        else:
            visual_style_preset = instance.data.get("visualStyleMode")
            nitrousGraphicMgr = rt.NitrousGraphicsManager
            viewport_setting = nitrousGraphicMgr.GetActiveViewportSetting()
            with viewport_setup(
                viewport_setting,
                visual_style_preset,
                review_camera):
                viewport_setting.VisualStyleMode = rt.Name(
                    visual_style_preset)
                preview_arg = set_preview_arg(
                    instance, filepath, frame, frame, fps)
                rt.execute(preview_arg)

        representation = {
            "name": "thumbnail",
            "ext": "png",
            "files": thumbnail,
            "stagingDir": tmp_staging,
            "thumbnail": True
        }

        self.log.debug(f"{representation}")

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)

    def get_filename(self, filename, target_frame):
        thumbnail_name = "{}_thumbnail.{:04}.png".format(
            filename, target_frame
        )
        return thumbnail_name
