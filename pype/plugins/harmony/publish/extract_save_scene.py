import pyblish.api
from avalon import harmony


class ExtractSaveScene(pyblish.api.ContextPlugin):
    """Save the scene."""

    label = "Extract Save Scene"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["harmony"]
    families = ["render"]

    def process(self, instance):
        harmony.send({"function": "scene.saveAll"})
