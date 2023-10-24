import pyblish.api

from openpype.pipeline import registered_host
from openpype.pipeline.publish import KnownPublishError


class Mrv2SaveCurrentWorkfile(pyblish.api.ContextPlugin):
    """Save current workfile"""

    label = "Save current workfile"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["mrv2"]
    families = ["workfile"]

    def process(self, context):

        assert context.data.get("currentFile"), "Must have `currentFile` data"

        # Filename must not have changed since collecting
        host = registered_host()  # type: Mrv2Host
        current_file = host.get_current_workfile()
        if context.data["currentFile"] != current_file:
            raise KnownPublishError(
                "Collected filename mismatches from current scene name."
            )

        self.log.debug(f"Saving current workfile: {current_file}")
        host.save_workfile(current_file)
