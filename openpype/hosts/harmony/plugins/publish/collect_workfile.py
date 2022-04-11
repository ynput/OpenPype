# -*- coding: utf-8 -*-
"""Collect current workfile from Harmony."""
import pyblish.api
import os

from openpype.lib import get_subset_name_with_asset_doc


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["harmony"]

    def process(self, context):
        """Plugin entry point."""
        family = "workfile"
        basename = os.path.basename(context.data["currentFile"])
        subset = get_subset_name_with_asset_doc(
            family,
            "",
            context.data["anatomyData"]["task"]["name"],
            context.data["assetEntity"],
            context.data["anatomyData"]["project"]["name"],
            host_name=context.data["hostName"]
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
