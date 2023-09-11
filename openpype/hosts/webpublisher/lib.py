import os
from datetime import datetime
import collections
import json

from bson.objectid import ObjectId

import pyblish.util
import pyblish.api

from openpype.client.mongo import OpenPypeMongoConnection
from openpype.settings import get_project_settings
from openpype.lib import Logger
from openpype.lib.profiles_filtering import filter_profiles

ERROR_STATUS = "error"
IN_PROGRESS_STATUS = "in_progress"
REPROCESS_STATUS = "reprocess"
SENT_REPROCESSING_STATUS = "sent_for_reprocessing"
FINISHED_REPROCESS_STATUS = "republishing_finished"
FINISHED_OK_STATUS = "finished_ok"

log = Logger.get_logger(__name__)


def parse_json(path):
    """Parses json file at 'path' location

        Returns:
            (dict) or None if unparsable
        Raises:
            AssertionError if 'path' doesn't exist
    """
    path = path.strip('\"')
    assert os.path.isfile(path), (
        "Path to json file doesn't exist. \"{}\"".format(path)
    )
    data = None
    with open(path, "r") as json_file:
        try:
            data = json.load(json_file)
        except Exception as exc:
            log.error(
                "Error loading json: {} - Exception: {}".format(path, exc)
            )
    return data


def get_batch_asset_task_info(ctx):
    """Parses context data from webpublisher's batch metadata

        Returns:
            (tuple): asset, task_name (Optional), task_type
    """
    task_type = "default_task_type"
    task_name = None
    asset = None

    if ctx["type"] == "task":
        items = ctx["path"].split('/')
        asset = items[-2]
        task_name = ctx["name"]
        task_type = ctx["attributes"]["type"]
    else:
        asset = ctx["name"]

    return asset, task_name, task_type


def find_close_plugin(close_plugin_name, log):
    if close_plugin_name:
        plugins = pyblish.api.discover()
        for plugin in plugins:
            if plugin.__name__ == close_plugin_name:
                return plugin

    log.debug("Close plugin not found, app might not close.")


def publish_in_test(log, close_plugin_name=None):
    """Loops through all plugins, logs to console. Used for tests.

    Args:
        log (Logger)
        close_plugin_name (Optional[str]): Name of plugin with responsibility
            to close application.
    """

    # Error exit as soon as any error occurs.
    error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

    close_plugin = find_close_plugin(close_plugin_name, log)

    for result in pyblish.util.publish_iter():
        for record in result["records"]:
            # Why do we log again? pyblish logger is logging to stdout...
            log.info("{}: {}".format(result["plugin"].label, record.msg))

        if not result["error"]:
            continue

        # QUESTION We don't break on error?
        error_message = error_format.format(**result)
        log.error(error_message)
        if close_plugin:  # close host app explicitly after error
            context = pyblish.api.Context()
            close_plugin().process(context)


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
        "status": IN_PROGRESS_STATUS,
        "progress": 0  # integer 0-100, percentage
    }).inserted_id


def publish_and_log(dbcon, _id, log, close_plugin_name=None, batch_id=None):
    """Loops through all plugins, logs ok and fails into OP DB.

        Args:
            dbcon (OpenPypeMongoConnection)
            _id (str) - id of current job in DB
            log (openpype.lib.Logger)
            batch_id (str) - id sent from frontend
            close_plugin_name (str): name of plugin with responsibility to
                close host app
    """
    # Error exit as soon as any error occurs.
    error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}\n"
    error_format += "-" * 80 + "\n"

    close_plugin = find_close_plugin(close_plugin_name, log)

    if isinstance(_id, str):
        _id = ObjectId(_id)

    log_lines = []
    processed = 0
    log_every = 5
    for result in pyblish.util.publish_iter():
        for record in result["records"]:
            log_lines.append("{}: {}".format(
                result["plugin"].label, record.msg))
        processed += 1

        if result["error"]:
            log.error(error_format.format(**result))
            log_lines = [error_format.format(**result)] + log_lines
            dbcon.update_one(
                {"_id": _id},
                {"$set":
                    {
                        "finish_date": datetime.now(),
                        "status": ERROR_STATUS,
                        "log": os.linesep.join(log_lines)

                    }}
            )
            if close_plugin:  # close host app explicitly after error
                context = pyblish.api.Context()
                close_plugin().process(context)
            return
        elif processed % log_every == 0:
            # pyblish returns progress in 0.0 - 2.0
            progress = min(round(result["progress"] / 2 * 100), 99)
            dbcon.update_one(
                {"_id": _id},
                {"$set":
                    {
                        "progress": progress,
                        "log": os.linesep.join(log_lines)
                    }}
            )

    # final update
    if batch_id:
        dbcon.update_many(
            {"batch_id": batch_id, "status": SENT_REPROCESSING_STATUS},
            {
                "$set":
                    {
                        "finish_date": datetime.now(),
                        "status": FINISHED_REPROCESS_STATUS,
                    }
            }
        )

    dbcon.update_one(
        {"_id": _id},
        {
            "$set":
                {
                    "finish_date": datetime.now(),
                    "status": FINISHED_OK_STATUS,
                    "progress": 100,
                    "log": os.linesep.join(log_lines)
                }
        }
    )


def fail_batch(_id, dbcon, msg):
    """Set current batch as failed as there is some problem.

    Raises:
        ValueError
    """
    dbcon.update_one(
        {"_id": _id},
        {"$set":
            {
                "finish_date": datetime.now(),
                "status": ERROR_STATUS,
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
    sorted_variants = collections.OrderedDict(
        sorted(app_group.variants.items()))
    for variant_key, variant in sorted_variants.items():
        for executable in variant.executables:
            if executable.exists():
                found_variant_key = variant_key

    if not found_variant_key:
        raise ValueError("No executable for {} found".format(host))

    return found_variant_key


def get_task_data(batch_dir):
    """Return parsed data from first task manifest.json

        Used for `publishfromapp` command where batch contains only
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


def get_timeout(project_name, host_name, task_type):
    """Returns timeout(seconds) from Setting profile."""
    filter_data = {
        "task_types": task_type,
        "hosts": host_name
    }
    timeout_profiles = (get_project_settings(project_name)["webpublisher"]
                                                          ["timeout_profiles"])
    matching_item = filter_profiles(timeout_profiles, filter_data)
    timeout = 3600
    if matching_item:
        timeout = matching_item["timeout"]

    return timeout
