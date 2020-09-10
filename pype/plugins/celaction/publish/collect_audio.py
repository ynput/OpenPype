import pyblish.api
import os

import pype.api as pype
from pprint import pformat


class AppendCelactionAudio(pyblish.api.ContextPlugin):

    label = "Colect Audio for publishing"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        self.log.info('Collecting Audio Data')
        asset_entity = context.data["assetEntity"]

        # get all available representations
        subsets = pype.get_subsets(asset_entity["name"],
                                   representations=["audio", "wav"]
                                   )
        self.log.info(f"subsets is: {pformat(subsets)}")

        if not subsets.get("audioMain"):
            raise AttributeError("`audioMain` subset does not exist")

        reprs = subsets.get("audioMain", {}).get("representations", [])
        self.log.info(f"reprs is: {pformat(reprs)}")

        repr = next((r for r in reprs), None)
        if not repr:
            raise "Missing `audioMain` representation"
        self.log.info(f"represetation is: {repr}")

        audio_file = repr.get('data', {}).get('path', "")

        if os.path.exists(audio_file):
            context.data["audioFile"] = audio_file
            self.log.info(
                'audio_file: {}, has been added to context'.format(audio_file))
        else:
            self.log.warning("Couldn't find any audio file on Ftrack.")
