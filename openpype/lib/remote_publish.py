import os
from datetime import datetime
import sys
from bson.objectid import ObjectId

import pyblish.util
import pyblish.api

from openpype import uninstall
from openpype.lib.mongo import OpenPypeMongoConnection
from openpype.lib.plugin_tools import parse_json


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
        "status": "in_progress",
        "progress": 0.0
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


def fail_batch(_id, batches_in_progress, dbcon):
    """Set current batch as failed as there are some stuck batches."""
    running_batches = [str(batch["_id"])
                       for batch in batches_in_progress
                       if batch["_id"] != _id]
    msg = "There are still running batches {}\n". \
        format("\n".join(running_batches))
    msg += "Ask admin to check them and reprocess current batch"
    dbcon.update_one(
        {"_id": _id},
        {"$set":
            {
                "finish_date": datetime.now(),
                "status": "error",
                "log": msg

            }}
    )
    raise ValueError(msg)


def find_variant_key(application_manager, host):
    """Searches for latest installed variant for 'host'

        Args:
            application_manager (ApplicationManager)
            host (str)
        Returns
            (string) (optional)
        Raises:
            (ValueError) if no variant found
    """
    app_group = application_manager.app_groups.get(host)
    if not app_group or not app_group.enabled:
        raise ValueError("No application {} configured".format(host))

    found_variant_key = None
    # finds most up-to-date variant if any installed
    for variant_key, variant in app_group.variants.items():
        for executable in variant.executables:
            if executable.exists():
                found_variant_key = variant_key

    if not found_variant_key:
        raise ValueError("No executable for {} found".format(host))

    return found_variant_key


def _get_close_plugin(close_plugin_name, log):
    if close_plugin_name:
        plugins = pyblish.api.discover()
        for plugin in plugins:
            if plugin.__name__ == close_plugin_name:
                return plugin

    log.warning("Close plugin not found, app might not close.")


def get_task_data(batch_dir):
    """Return parsed data from first task manifest.json

        Used for `remotepublishfromapp` command where batch contains only
        single task with publishable workfile.

        Returns:
            (dict)
        Throws:
            (ValueError) if batch or task manifest not found or broken
    """
    batch_data = parse_json(os.path.join(batch_dir, "manifest.json"))
    if not batch_data:
        raise ValueError(
            "Cannot parse batch meta in {} folder".format(batch_dir))
    task_dir_name = batch_data["tasks"][0]
    task_data = parse_json(os.path.join(batch_dir, task_dir_name,
                                        "manifest.json"))
    if not task_data:
        raise ValueError(
            "Cannot parse batch meta in {} folder".format(task_data))

    return task_data
