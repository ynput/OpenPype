import pyblish.api

import openpype.api
from openpype.hosts.aftereffects.api import get_stub


class ExtractSaveScene(pyblish.api.ContextPlugin):
    """Save scene before extraction."""

    order = openpype.api.Extractor.order - 0.48
    label = "Extract Save Scene"
    hosts = ["aftereffects"]

    def process(self, context):
        stub = get_stub()
        stub.save()
