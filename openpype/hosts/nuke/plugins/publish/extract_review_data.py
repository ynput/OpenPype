import os
from pprint import pformat
import pyblish.api

from openpype.pipeline import publish


class ExtractReviewData(publish.Extractor):
    """Extracts review tag into available representation
    """

    order = pyblish.api.ExtractorOrder + 0.01
    # order = pyblish.api.CollectorOrder + 0.499
    label = "Extract Review Data"

    families = ["review"]
    hosts = ["nuke"]

    def process(self, instance):
        fpath = instance.data["path"]
        ext = os.path.splitext(fpath)[-1][1:]

        representations = instance.data.get("representations", [])

        # review can be removed since `ProcessSubmittedJobOnFarm` will create
        # reviewable representation if needed
        if (
            instance.data.get("farm")
            and "review" in instance.data["families"]
        ):
            instance.data["families"].remove("review")

        # iterate representations and add `review` tag
        for repre in representations:
            if ext != repre["ext"]:
                continue

            if not repre.get("tags"):
                repre["tags"] = []

            if "review" not in repre["tags"]:
                repre["tags"].append("review")

            self.log.debug("Matching representation: {}".format(
                pformat(repre)
            ))

        instance.data["representations"] = representations
