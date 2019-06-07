from pyblish import api
import os
import time


class ExtractPlateCheck(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.ExtractorOrder + 0.01
    label = "Plates Export Waiting"
    hosts = ["nukestudio"]
    families = ["encode"]

    def process(self, context):

        plate_path = context.data.get("platesCheck", None)

        self.log.info("Chacking plate: `{}`".format(plate_path))

        if not plate_path:
            return

        while not os.path.exists(plate_path):
            self.log.info("Waiting for plates to be rendered")
            time.sleep(5)

        if os.path.isfile(plate_path):
            self.log.info("Plates were rendered: `{}`".format(plate_path))
        else:
            raise ValueError("%s isn't a file!" % plate_path)
