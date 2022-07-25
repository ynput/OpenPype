import pyblish.api
import openpype.hosts.harmony.api as harmony


class ExtractSaveScene(pyblish.api.ContextPlugin):
    """Save scene for extraction."""

    label = "Extract Save Scene"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["harmony"]

    def process(self, context):
        harmony.save_scene()
