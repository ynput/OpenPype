import os
from datetime import datetime
import sys
from bson.objectid import ObjectId

import pyblish.util
import pyblish.api

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


def publish_and_log(dbcon, _id, log, close_plugin_name=None):
    """Loops through all plugins, logs ok and fails into OP DB.

        Args:
            dbcon (OpenPypeMongoConnection)
            _id (str)
            log (OpenPypeLogger)
            close_plugin_name (str): name of plugin with responsibility to
                close host app
    """
    # Error exit as soon as any error occurs.
    error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

    close_plugin = _get_close_plugin(close_plugin_name, log)

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
            if close_plugin:  # close host app explicitly after error
                context = pyblish.api.Context()
                close_plugin().process(context)
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


def _get_close_plugin(close_plugin_name, log):
    if close_plugin_name:
        plugins = pyblish.api.discover()
        for plugin in plugins:
            if plugin.__name__ == close_plugin_name:
                return plugin

    log.warning("Close plugin not found, app might not close.")
