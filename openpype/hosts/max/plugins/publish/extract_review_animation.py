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
        filename = "{0}..{1}".format(instance.name, ext)
        start = int(instance.data["frameStart"])
        end = int(instance.data["frameEnd"])
        filepath = os.path.join(staging_dir, filename)
        filepath = filepath.replace("\\", "/")

        self.log.debug(
            "Writing Review Animation to"
            " '%s' to '%s'" % (filename, staging_dir))

        review_camera = instance.data["review_camera"]
        viewport_options = instance.data.get("viewport_options", {})
        resolution = instance.data.get("resolution", ())
        files = render_preview_animation(
            os.path.join(staging_dir, instance.name),
            ext,
            review_camera,
            start,
            end,
            width=resolution[0],
            height=resolution[1],
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
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "tags": tags,
            "preview": True,
            "camera_name": review_camera
        }
        self.log.debug(f"{representation}")

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)
