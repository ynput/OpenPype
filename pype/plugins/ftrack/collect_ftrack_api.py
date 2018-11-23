import os
import json
import base64

import ftrack_api
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

        try:
            decoded_event_data = json.loads(
                base64.b64decode(
                    os.environ.get("FTRACK_CONNECT_EVENT")
                )
            )

            task_id = decoded_event_data.get("selection")[0]["entityId"]
        except:
            pass

        context.data["ftrackTask"] = session.get("Task", task_id)
