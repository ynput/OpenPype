from pathlib import Path
import pyblish.api

from openpype.hosts.gaffer.api import get_root
from openpype.pipeline import registered_host


class GafferSaveScript(pyblish.api.ContextPlugin):
    """Save current Gaffer script"""

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["gaffer"]
    families = ["workfile"]

    def process(self, context):

        script = context.data.get("currentScript")
        assert script, "Must have script"

        # ensure we're processing on the correct gaffer script still
        assert get_root() == script, "Current gaffer script has changed"

        host = registered_host()

        # ensure we're still processing the same workfile name
        current_file = host.get_current_workfile()
        assert Path(current_file) == Path(context.data["currentFile"])
        host.save_workfile()

        self.log.info("Saving current file: %s", current_file)
