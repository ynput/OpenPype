from pathlib import Path

import pyblish.api

from openpype.lib import version_up
from openpype.pipeline import registered_host
from openpype.pipeline import publish


class GafferIncrementCurrentFile(pyblish.api.ContextPlugin,
                                 publish.OptionalPyblishPluginMixin):
    """Increment the current file.

    Saves the current scene with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["gaffer"]
    families = ["workfile"]
    optional = True

    def process(self, context):
        if not self.is_active(context.data):
            return

        # Filename must not have changed since collecting
        host = registered_host()
        current_file = host.get_current_workfile()
        if Path(current_file) != Path(context.data["currentFile"]):
            raise publish.KnownPublishError(
                "Collected filename mismatches from current scene name."
            )

        new_filepath = version_up(current_file)
        host.save_workfile(new_filepath)
