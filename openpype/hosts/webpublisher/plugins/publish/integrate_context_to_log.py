import os

import pyblish.api
from openpype.lib import OpenPypeMongoConnection


class IntegrateContextToLog(pyblish.api.ContextPlugin):
    """ Adds context information to log document for displaying in front end"""

    label = "Integrate Context to Log"
    order = pyblish.api.IntegratorOrder - 0.1
    hosts = ["webpublisher"]

    def process(self, context):
        self.log.info("Integrate Context to Log")

        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        database_name = os.environ["OPENPYPE_DATABASE_NAME"]
        dbcon = mongo_client[database_name]["webpublishes"]

        for instance in context:
            self.log.info("ctx_path: {}".format(instance.data.get("ctx_path")))
            self.log.info("batch_id: {}".format(instance.data.get("batch_id")))
            if instance.data.get("ctx_path") and instance.data.get("batch_id"):
                self.log.info("Updating log record")
                dbcon.update_one(
                    {
                        "batch_id": instance.data.get("batch_id"),
                        "status": "in_progress"
                    },
                    {"$set":
                        {
                            "path": instance.data.get("ctx_path")

                        }}
                )

                return
