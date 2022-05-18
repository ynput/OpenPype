"""Parses batch context from json and continues in publish process.

Provides:
    context -> Loaded batch file.
        - asset
        - task  (task name)
        - taskType
        - project_name
        - variant

Code is practically copy of `openype/hosts/webpublish/collect_batch_data` as
webpublisher should be eventually ejected as an addon, eg. mentioned plugin
shouldn't be pushed into general publish plugins.
"""

import os

import pyblish.api

from openpype.lib.plugin_tools import (
    parse_json,
    get_batch_asset_task_info
)
from openpype.pipeline import legacy_io


class CollectBatchData(pyblish.api.ContextPlugin):
    """Collect batch data from json stored in 'OPENPYPE_PUBLISH_DATA' env dir.

    The directory must contain 'manifest.json' file where batch data should be
    stored.
    """
    # must be really early, context values are only in json file
    order = pyblish.api.CollectorOrder - 0.495
    label = "Collect batch data"
    hosts = ["photoshop"]
    targets = ["remotepublish"]

    def process(self, context):
        self.log.info("CollectBatchData")
        batch_dir = os.environ.get("OPENPYPE_PUBLISH_DATA")
        if (os.environ.get("IS_TEST") and
                (not batch_dir or not os.path.exists(batch_dir))):
            self.log.debug("Automatic testing, no batch data, skipping")
            return

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
        os.environ["AVALON_TASK"] = task_name
        legacy_io.Session["AVALON_ASSET"] = asset_name
        legacy_io.Session["AVALON_TASK"] = task_name

        context.data["asset"] = asset_name
        context.data["task"] = task_name
        context.data["taskType"] = task_type
        context.data["project_name"] = project_name
        context.data["variant"] = batch_data["variant"]
