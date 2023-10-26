import os
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
        ext = instance.data.get("imageFormat")
        frame = int(instance.data["frameStart"])
        staging_dir = self.staging_dir(instance)
        filepath = os.path.join(
            staging_dir, f"{instance.name}_thumbnail")
        self.log.debug("Writing Thumbnail to '{}'".format(filepath))

        review_camera = instance.data["review_camera"]
        viewport_options = instance.data.get("viewport_options", {})
        files = render_preview_animation(
            filepath,
            ext,
            review_camera,
            start_frame=frame,
            end_frame=frame,
            percentSize=instance.data["percentSize"],
            width=instance.data["review_width"],
            height=instance.data["review_height"],
            viewport_options=viewport_options)

        thumbnail = next(os.path.basename(path) for path in files)

        representation = {
            "name": "thumbnail",
            "ext": ext,
            "files": thumbnail,
            "stagingDir": staging_dir,
            "thumbnail": True
        }

        self.log.debug(f"{representation}")

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)
