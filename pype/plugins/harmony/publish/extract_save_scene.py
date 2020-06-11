import pyblish.api
from avalon import harmony


class ExtractSaveScene(pyblish.api.ContextPlugin):
    """Save scene for extraction."""

    label = "Extract Save Scene"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["harmony"]

    def process(self, instance):
        harmony.save_scene()
