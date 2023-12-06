import os
import pyblish.api

from openpype.pipeline import publish


class ExtractGafferScript(
    publish.Extractor,
    publish.OpenPypePyblishPluginMixin
):
    """Render the current Fusion composition locally."""

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Gaffer Script"
    hosts = ["gaffer"]
    families = ["gafferScene"]

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
