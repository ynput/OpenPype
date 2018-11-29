import os

import ftrack_api_old as ftrack_api
import pyblish.api


class CollectFtrackApi(pyblish.api.ContextPlugin):
    """ Collects an ftrack session and the current task id. """

    order = pyblish.api.CollectorOrder
    label = "Collect Ftrack Api"

    def process(self, context):

        # Collect session
        session = ftrack_api.Session()
        context.data["ftrackSession"] = session

        # Collect task
        task_id = os.environ.get("FTRACK_TASKID", "")

        context.data["ftrackTask"] = session.get("Task", task_id)
