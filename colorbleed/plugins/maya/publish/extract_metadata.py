import os
import json
import colorbleed.api


class ExtractMetadata(colorbleed.api.Extractor):
    """Extract origin metadata from scene"""

    label = "Metadata"

    def process(self, instance):

        temp_dir = self.staging_dir(instance)
        temp_file = os.path.join(temp_dir, "metadata.meta")

        metadata = instance.data("metadata")
        self.log.info("Extracting %s" % metadata)
        with open(temp_file, "w") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)

        self.log.info("Written to %s" % temp_file)
