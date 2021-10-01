import pyblish.api
import os

from pype import lib
from avalon.tvpaint import HEADLESS


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder
    label = "Collect Workfile"
    hosts = ["tvpaint"]

    def process(self, context):
        if HEADLESS:
            return

        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        file_path = context.data["currentFile"]
        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        subset = lib.get_subset_name(
            "workfile",
            "",
            task,
            context.data["assetEntity"]["_id"],
            host_name="tvpaint"
        )

        # Create instance
        data = {
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "family": family,
            "families": [family],
            "representations": list(),
            "asset": os.environ["AVALON_ASSET"]
        }
        instance = context.create_instance(**data)

        # creating representation
        representation = {
            "name": "tvpp",
            "ext": "tvpp",
            "files": base_name,
            "stagingDir": staging_dir,
        }

        instance.data["representations"].append(representation)
