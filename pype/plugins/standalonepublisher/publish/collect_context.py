"""
Requires:
    environment     -> SAPUBLISH_INPATH
    environment     -> SAPUBLISH_OUTPATH

Provides:
    context         -> returnJsonPath (str)
    context         -> project
    context         -> asset
    instance        -> destination_list (list)
    instance        -> representations (list)
    instance        -> source (list)
    instance        -> representations
"""

import os
import pyblish.api
from avalon import io
import json
import logging
import clique

log = logging.getLogger("collector")


class CollectContextDataSAPublish(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.
    """

    label = "Collect Context - SA Publish"
    order = pyblish.api.CollectorOrder - 0.49
    hosts = ["standalonepublisher"]

    def process(self, context):
        # get json paths from os and load them
        io.install()
        input_json_path = os.environ.get("SAPUBLISH_INPATH")
        output_json_path = os.environ.get("SAPUBLISH_OUTPATH")

        # context.data["stagingDir"] = os.path.dirname(input_json_path)
        context.data["returnJsonPath"] = output_json_path

        with open(input_json_path, "r") as f:
            in_data = json.load(f)

        asset_name = in_data["asset"]
        family = in_data["family"]
        subset = in_data["subset"]

        # Load presets
        presets = context.data.get("presets")
        if not presets:
            from pype.api import config

            presets = config.get_presets()

        project = io.find_one({"type": "project"})
        asset = io.find_one({"type": "asset", "name": asset_name})
        context.data["project"] = project
        context.data["asset"] = asset

        instance = context.create_instance(subset)

        instance.data.update(
            {
                "subset": subset,
                "asset": asset_name,
                "label": subset,
                "name": subset,
                "family": family,
                "version": in_data.get("version", 1),
                "frameStart": in_data.get("representations", [None])[0].get(
                    "frameStart", None
                ),
                "frameEnd": in_data.get("representations", [None])[0].get(
                    "frameEnd", None
                ),
                "families": [family, "ftrack"],
            }
        )
        self.log.info("collected instance: {}".format(instance.data))
        self.log.info("parsing data: {}".format(in_data))

        instance.data["destination_list"] = list()
        instance.data["representations"] = list()
        instance.data["source"] = "standalone publisher"

        for component in in_data["representations"]:
            component["destination"] = component["files"]
            component["stagingDir"] = component["stagingDir"]

            if isinstance(component["files"], list):
                collections, remainder = clique.assemble(component["files"])
                self.log.debug("collecting sequence: {}".format(collections))
                instance.data["frameStart"] = int(component["frameStart"])
                instance.data["frameEnd"] = int(component["frameEnd"])
                instance.data["fps"] = int(component["fps"])

            if component["preview"]:
                instance.data["families"].append("review")
                instance.data["repreProfiles"] = ["h264"]
                component["tags"] = ["review"]
                self.log.debug("Adding review family")

            instance.data["representations"].append(component)

        self.log.info(in_data)
