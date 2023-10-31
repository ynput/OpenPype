import os
import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.max.api.preview_animation import (
    render_preview_animation
)


class ExtractReviewAnimation(publish.Extractor):
    """
    Extract Review by Review Animation
    """

    order = pyblish.api.ExtractorOrder + 0.001
    label = "Extract Review Animation"
    hosts = ["max"]
    families = ["review"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        ext = instance.data.get("imageFormat")
        start = int(instance.data["frameStart"])
        end = int(instance.data["frameEnd"])
        filepath = os.path.join(staging_dir, instance.name)
        self.log.debug(
            "Writing Review Animation to '{}'".format(filepath))

        review_camera = instance.data["review_camera"]
        viewport_options = instance.data.get("viewport_options", {})
        files = render_preview_animation(
            filepath,
            ext,
            review_camera,
            start,
            end,
            percentSize=instance.data["percentSize"],
            width=instance.data["review_width"],
            height=instance.data["review_height"],
            viewport_options=viewport_options)

        filenames = [os.path.basename(path) for path in files]

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        self.log.debug("Performing Extraction ...")

        representation = {
            "name": instance.data["imageFormat"],
            "ext": instance.data["imageFormat"],
            "files": filenames,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStartHandle"],
            "frameEnd": instance.data["frameEndHandle"],
            "tags": tags,
            "preview": True,
            "camera_name": review_camera
        }
        self.log.debug(f"{representation}")

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)
