import json
import os
import re

import pyblish.api


class ExtractImageSequence(pyblish.api.Extractor):
    """Extract result of saver by starting a comp render

    This will run the local render of Fusion,
    """

    order = pyblish.api.ExtractorOrder
    label = "Render Local"
    hosts = ["fusion"]
    targets = ["renderlocal"]

    def process(self, context):

        current_comp = context.data["currentComp"]
        start_frame = current_comp.GetAttrs("COMPN_RenderStart")
        end_frame = current_comp.GetAttrs("COMPN_RenderEnd")

        # Build Fusion Render Job
        self.log.info("Starting render")
        self.log.info("Start frame: {}".format(start_frame))
        self.log.info("End frame: {}".format(end_frame))

        result = current_comp.Render()
        if not result:
            raise RuntimeError("Comp render failed")

        # Write metadata json file per Saver instance
        instances = [i for i in context[:] if i[0].ID == "Saver"]
        for instance in instances:
            subset = instance.data["subset"]
            ext = instance.data["ext"]

            # Regex to match resulting renders
            regex = "^{subset}.*[0-9]+.{ext}+$".format(subset=re.escape(subset)
                                                       , ext=re.escape(ext))

            # The instance has most of the information already stored
            metadata = {
                "regex": regex,
                "startFrame": context.data["startFrame"],
                "endFrame": context.data["endFrame"],
                "families": ["colorbleed.imagesequence"],
            }

            # Write metadata and store the path in the instance
            output_directory = instance.data["outputDir"]
            path = os.path.join(output_directory,
                                "{}_metadata.json".format(subset))

            with open(path, "w") as f:
                json.dump(metadata, f)

            # Store json path in instance
            instance.data["jsonpath"] = path
