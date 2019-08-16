import pyblish.api
import os
import json


class ExtractVideoTracksEffects(pyblish.api.InstancePlugin):
    """Collect video tracks effects into context."""

    order = pyblish.api.CollectorOrder + 0.1018
    label = "Export Effects"
    femilies = ["effects"]

    def process(self, instance):
        effects = instance.data.get("effectTrackItems")
        subset = instance.data.get("subset")

        if effects:
            self.log.info("_ subset: `{}`".format(subset))
            for ef in effects.keys():
                self.log.info("_ ef: `{}`".format(ef))
