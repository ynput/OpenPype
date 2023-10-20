import os
import tempfile
import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.max.api.preview_animation import render_preview_animation


class ExtractThumbnail(publish.Extractor):
    """Extract Thumbnail for Review
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
        ext = instance.data.get("imageFormat")
        frame = int(instance.data["frameStart"])
        instance.context.data["cleanupFullPaths"].append(tmp_staging)
        filepath = os.path.join(tmp_staging, instance.name)

        self.log.debug("Writing Thumbnail to '{}'".format(filepath))

        review_camera = instance.data["review_camera"]
        viewport_options = instance.data.get("viewport_options", {})
        files = render_preview_animation(
            filepath,
            ext,
            review_camera,
            frame,
            frame,
            width=instance.data["review_width"],
            height=instance.data["review_height"],
            viewport_options=viewport_options)

        thumbnail = next(os.path.basename(path) for path in files)

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
