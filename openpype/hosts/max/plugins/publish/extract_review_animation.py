import os
import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.max.api.lib import publish_preview_animation


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
        filenames = self.get_files(
            instance.name, start, end, ext)

        self.log.debug(
            "Writing Review Animation to"
            " '%s' to '%s'" % (filename, staging_dir))

        review_camera = instance.data["review_camera"]
        publish_preview_animation(
            instance, staging_dir,
            ext, review_camera,
            startFrame=start, endFrame=end)

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

    def get_files(self, filename, start, end, ext):
        file_list = []
        for frame in range(int(start), int(end) + 1):
            actual_name = "{}.{:04}.{}".format(
                filename, frame, ext)
            file_list.append(actual_name)

        return file_list
