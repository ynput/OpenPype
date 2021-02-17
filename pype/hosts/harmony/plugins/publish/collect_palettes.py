# -*- coding: utf-8 -*-
"""Collect palettes from Harmony."""
import os
import json

import pyblish.api
from avalon import harmony


class CollectPalettes(pyblish.api.ContextPlugin):
    """Gather palettes from scene when publishing templates."""

    label = "Palettes"
    order = pyblish.api.CollectorOrder
    hosts = ["harmony"]

    def process(self, context):
        """Collector entry point."""
        self_name = self.__class__.__name__
        palettes = harmony.send(
            {
                "function": f"PypeHarmony.Publish.{self_name}.getPalettes",
            })["result"]

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
