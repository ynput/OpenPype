import pyblish.api

from openpype.hosts.gaffer.api import get_root


class CollectCurrentScriptGaffer(pyblish.api.ContextPlugin):
    """Collect current Gaffer script"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Collect Current Script"
    hosts = ["gaffer"]

    def process(self, context):
        """Collect all image sequence tools"""

        script = get_root()
        assert script, "Must have active Gaffer script"
        context.data["currentScript"] = script

        # Store path to current file
        filepath = script["fileName"].getValue()
        context.data['currentFile'] = filepath
