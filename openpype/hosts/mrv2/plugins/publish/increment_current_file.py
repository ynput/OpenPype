import pyblish.api

from openpype.lib import version_up
from openpype.pipeline import registered_host
from openpype.pipeline.publish import (
    KnownPublishError,
    OptionalPyblishPluginMixin
)


class IncrementCurrentFile(pyblish.api.ContextPlugin,
                           OptionalPyblishPluginMixin):
    """Increment the current file.

    Saves the current scene with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["mrv2"]
    families = ["workfile"]
    optional = True

    def process(self, context):
        if not self.is_active(context.data):
            return

        # Filename must not have changed since collecting
        host = registered_host()  # type: Mrv2Host
        current_file = host.get_current_workfile()
        if context.data["currentFile"] != current_file:
            raise KnownPublishError(
                "Collected filename mismatches from current scene name."
            )

        new_filepath = version_up(current_file)
        host.save_workfile(new_filepath)
