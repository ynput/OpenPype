import os
import pyblish.api
from openpype.hosts.openrv.api.pipeline import get_containers
from openpype.pipeline import (
    legacy_io
)


class CollectSessionContainers(pyblish.api.ContextPlugin):
    """Collect session containers
    """

    order = pyblish.api.CollectorOrder - 0.01
    label = "Collect Session Containers"
    hosts = ["openrv"]
    family = "containers"

    def process(self, context):
        """Inject the current camera output and file"""

        task = legacy_io.Session["AVALON_TASK"]
        item_collection = get_containers()

        # create instances
        for item in item_collection:
            self.log.debug(item)
            item_name = item["namespace"]
            instance = context.create_instance(name=str(item_name))
            subset = 'container' + task.capitalize()

            data = {}
            data.update({
                "subset": subset,
                "asset": os.getenv("AVALON_ASSET", None),
                "label": str(item_name),
                "publish": False,
                "family": 'containers',
                "setMembers": [""],
                "frameStart": context.data['frameStart'],
                "frameEnd": context.data['frameEnd'],
                "handleStart": context.data['handleStart'],
                "handleEnd": context.data['handleEnd'],
            })

            instance.data.update(data)
