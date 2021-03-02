import os

import pyblish.api
from pype import api as pype_api
from avalon import api, io


class CollectAudio(pyblish.api.ContextPlugin):
    """Finds asset audio based on plugin settings."""

    order = pyblish.api.CollectorOrder
    label = "Collect Audio"

    subset_name = "audioMain"

    def process(self, context):
        version = pype_api.get_latest_version(
            api.Session["AVALON_ASSET"], self.subset_name
        )

        if version is None:
            self.log.warning(
                "No audio version found on subset name: \"{}\"".format(
                    self.subset_name
                )
            )
            return

        representation = io.find_one(
            {"type": "representation", "parent": version["_id"], "name": "wav"}
        )

        if representation is None:
            msg = (
                "No audio \"wav\" representation found on subset name: \"{}\""
            )
            self.log.warning(msg.format(self.subset_name))
            return

        path = api.get_representation_path(representation)

        if not os.path.exists(path):
            self.log.warning("No file found at: \"{}\"".format(path))
            return

        self.log.info("Using audio file: \"{}\"".format(path))
        context.data["audioFile"] = path
