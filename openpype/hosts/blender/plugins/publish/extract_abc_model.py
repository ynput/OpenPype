import pyblish.api
from openpype.pipeline import publish


class ExtractModelABC(publish.Extractor):
    """Extract model as ABC."""

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract Model ABC"
    hosts = ["blender"]
    families = ["model"]
    optional = True

    def process(self, instance):
        # Add abc.export family to the instance, to allow the extraction
        # as alembic of the asset.
        instance.data["families"].append("abc.export")
