# -*- coding: utf-8 -*-
"""Collect current workfile from Harmony."""
import os

import pyblish.api
from pype import lib


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["harmony"]

    def process(self, context):
        """Plugin entry point."""
        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        basename = os.path.basename(context.data["currentFile"])
        subset = lib.get_subset_name(
            "workfile",
            "",
            task,
            context.data["assetEntity"]["_id"],
            host_name="harmony"
        )

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
