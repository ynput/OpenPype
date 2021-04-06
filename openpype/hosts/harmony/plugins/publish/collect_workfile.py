# -*- coding: utf-8 -*-
"""Collect current workfile from Harmony."""
import pyblish.api
import os


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["harmony"]

    def process(self, context):
        """Plugin entry point."""
        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        sanitized_task_name = task[0].upper() + task[1:]
        basename = os.path.basename(context.data["currentFile"])
        subset = "{}{}".format(family, sanitized_task_name)

        # Create instance
        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "label": basename,
            "name": basename,
            "family": family,
            "families": [family],
            "representations": [],
            "asset": os.environ["AVALON_ASSET"]
        })
