import os
from datetime import datetime
import sys
from bson.objectid import ObjectId

import pyblish.util

from openpype import uninstall
from openpype.lib.mongo import OpenPypeMongoConnection


def get_webpublish_conn():
    """Get connection to OP 'webpublishes' collection."""
    mongo_client = OpenPypeMongoConnection.get_mongo_client()
    database_name = os.environ["OPENPYPE_DATABASE_NAME"]
    return mongo_client[database_name]["webpublishes"]


def start_webpublish_log(dbcon, batch_id, user):
    """Start new log record for 'batch_id'

        Args:
            dbcon (OpenPypeMongoConnection)
            batch_id (str)
            user (str)
        Returns
            (ObjectId) from DB
    """
    return dbcon.insert_one({
        "batch_id": batch_id,
        "start_date": datetime.now(),
        "user": user,
        "status": "in_progress"
    }).inserted_id


def publish_and_log(dbcon, _id, log):
    """Loops through all plugins, logs ok and fails into OP DB.

        Args:
            dbcon (OpenPypeMongoConnection)
            _id (str)
            log (OpenPypeLogger)
    """
    # Error exit as soon as any error occurs.
    error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

    if isinstance(_id, str):
        _id = ObjectId(_id)

    log_lines = []
    for result in pyblish.util.publish_iter():
        for record in result["records"]:
            log_lines.append("{}: {}".format(
                result["plugin"].label, record.msg))

        if result["error"]:
            log.error(error_format.format(**result))
            uninstall()
            log_lines.append(error_format.format(**result))
            dbcon.update_one(
                {"_id": _id},
                {"$set":
                    {
                        "finish_date": datetime.now(),
                        "status": "error",
                        "log": os.linesep.join(log_lines)

                    }}
            )
            sys.exit(1)
        else:
            dbcon.update_one(
                {"_id": _id},
                {"$set":
                    {
                        "progress": max(result["progress"], 0.95),
                        "log": os.linesep.join(log_lines)
                    }}
            )

    # final update
    dbcon.update_one(
        {"_id": _id},
        {"$set":
            {
                "finish_date": datetime.now(),
                "status": "finished_ok",
                "progress": 1,
                "log": os.linesep.join(log_lines)
            }}
    )