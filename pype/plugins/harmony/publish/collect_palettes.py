# -*- coding: utf-8 -*-
"""Collect palettes from Harmony."""
import os
import json

import pyblish.api
from avalon import harmony


class CollectPalettes(pyblish.api.ContextPlugin):
    """Gather palettes from scene when publishing templates."""

    label = "Palettes"
    order = pyblish.api.CollectorOrder + 0.003
    hosts = ["harmony"]
    allowed_tasks = []  # list of task names where collecting should happen

    def process(self, context):
        """Collector entry point."""
        self_name = self.__class__.__name__
        palettes = harmony.send(
            {
                "function": f"PypeHarmony.Publish.{self_name}.getPalettes",
            })["result"]

        # skip collecting if not in allowed task
        if self.allowed_tasks:
            self.allowed_tasks = [task.lower() for task in self.allowed_tasks]
            if context.data["anatomyData"]["task"].lower() \
                    not in self.allowed_tasks:
                return

        for name, id in palettes.items():
            instance = context.create_instance(name)
            instance.data.update({
                "id": id,
                "family": "harmony.palette",
                'families': [],
                "asset": os.environ["AVALON_ASSET"],
                "subset": "{}{}".format("palette", name)
            })
            self.log.info(
                "Created instance:\n" + json.dumps(
                    instance.data, sort_keys=True, indent=4
                )
            )
