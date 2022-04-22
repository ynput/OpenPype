"""Parses batch context from json and continues in publish process.

Provides:
    context -> Loaded batch file.
        - asset
        - task  (task name)
        - taskType
        - project_name
        - variant
"""

import os

import pyblish.api
from avalon import io
from openpype.lib.plugin_tools import (
    parse_json,
    get_batch_asset_task_info
)
from openpype.lib.remote_publish import get_webpublish_conn, IN_PROGRESS_STATUS


class CollectBatchData(pyblish.api.ContextPlugin):
    """Collect batch data from json stored in 'OPENPYPE_PUBLISH_DATA' env dir.

    The directory must contain 'manifest.json' file where batch data should be
    stored.
    """
    # must be really early, context values are only in json file
    order = pyblish.api.CollectorOrder - 0.495
    label = "Collect batch data"
    hosts = ["webpublisher"]

    def process(self, context):
        batch_dir = os.environ.get("OPENPYPE_PUBLISH_DATA")

        assert batch_dir, (
            "Missing `OPENPYPE_PUBLISH_DATA`")

        assert os.path.exists(batch_dir), \
            "Folder {} doesn't exist".format(batch_dir)

        project_name = os.environ.get("AVALON_PROJECT")
        if project_name is None:
            raise AssertionError(
                "Environment `AVALON_PROJECT` was not found."
                "Could not set project `root` which may cause issues."
            )

        batch_data = parse_json(os.path.join(batch_dir, "manifest.json"))

        context.data["batchDir"] = batch_dir
        context.data["batchData"] = batch_data

        asset_name, task_name, task_type = get_batch_asset_task_info(
            batch_data["context"]
        )

        os.environ["AVALON_ASSET"] = asset_name
        io.Session["AVALON_ASSET"] = asset_name
        os.environ["AVALON_TASK"] = task_name
        io.Session["AVALON_TASK"] = task_name

        context.data["asset"] = asset_name
        context.data["task"] = task_name
        context.data["taskType"] = task_type
        context.data["project_name"] = project_name
        context.data["variant"] = batch_data["variant"]

        self._set_ctx_path(batch_data)

    def _set_ctx_path(self, batch_data):
        dbcon = get_webpublish_conn()

        batch_id = batch_data["batch"]
        ctx_path = batch_data["context"]["path"]
        self.log.info("ctx_path: {}".format(ctx_path))
        self.log.info("batch_id: {}".format(batch_id))
        if ctx_path and batch_id:
            self.log.info("Updating log record")
            dbcon.update_one(
                {
                    "batch_id": batch_id,
                    "status": IN_PROGRESS_STATUS
                },
                {
                    "$set": {
                        "path": ctx_path
                    }
                }
            )
