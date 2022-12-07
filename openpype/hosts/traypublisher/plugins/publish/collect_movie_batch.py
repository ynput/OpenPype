import os

import pyblish.api
from openpype.pipeline import OpenPypePyblishPluginMixin


class CollectMovieBatch(
    pyblish.api.InstancePlugin, OpenPypePyblishPluginMixin
):
    """Collect file url for batch movies and create representation.

    Adds review on instance and to repre.tags based on value of toggle button
    on creator.
    """

    label = "Collect Movie Batch Files"
    order = pyblish.api.CollectorOrder

    hosts = ["traypublisher"]

    def process(self, instance):
        if instance.data.get("creator_identifier") != "render_movie_batch":
            return

        creator_attributes = instance.data["creator_attributes"]

        file_url = creator_attributes["filepath"]
        file_name = os.path.basename(file_url)
        _, ext = os.path.splitext(file_name)

        repre = {
            "name": ext[1:],
            "ext": ext[1:],
            "files": file_name,
            "stagingDir": os.path.dirname(file_url),
            "tags": []
        }
        instance.data["representations"].append(repre)

        if creator_attributes["add_review_family"]:
            repre["tags"].append("review")
            instance.data["families"].append("review")
            if not instance.data.get("thumbnailSource"):
                instance.data["thumbnailSource"] = file_url

        instance.data["source"] = file_url

        self.log.debug("instance.data {}".format(instance.data))
