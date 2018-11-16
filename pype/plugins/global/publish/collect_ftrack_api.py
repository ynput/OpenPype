import os

import ftrack_api_27 as ftrack_api
import pyblish.api


class PyblishFtrackCollectFtrackApi(pyblish.api.ContextPlugin):
    """ Collects an ftrack session and the current task id. """

    order = pyblish.api.CollectorOrder
    label = "Ftrack"

    def process(self, context):

        # Collect session
        session = ftrack_api.Session()
        context.data["ftrackSession"] = session

        # Collect task
        taskid = ""

        taskid = os.environ.get("FTRACK_TASKID", "")

        context.data["ftrackTask"] = session.get("Task", taskid)

        self.log.info("collected: {}".format(context.data["ftrackTask"]))
