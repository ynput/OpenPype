import os
import pyblish.api

from openpype.pipeline import publish


class ExtractGafferNodes(
    publish.Extractor,
    publish.OpenPypePyblishPluginMixin
):
    """Export box nodes for reference."""

    order = pyblish.api.ExtractorOrder
    label = "Gaffer Script"
    hosts = ["gaffer"]
    families = ["gafferNodes"]

    def process(self, instance):

        node = instance.data["transientData"]["node"]

        staging_dir = self.staging_dir(instance)
        filepath = os.path.join(staging_dir, f"{instance.name}.gfr")

        # Export node
        node.exportForReference(filepath)

        # Add representation to instance
        representation = {
            "name": "gfr",
            "ext": "gfr",
            "files": os.path.basename(filepath),
            "stagingDir": staging_dir,
        }
        representations = instance.data.setdefault("representations", [])
        representations.append(representation)
