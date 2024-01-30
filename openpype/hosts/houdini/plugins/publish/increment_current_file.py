import pyblish.api

from openpype.lib import version_up
from openpype.pipeline import registered_host
from openpype.pipeline.publish import get_errored_plugins_from_context
from openpype.hosts.houdini.api import HoudiniHost
from openpype.pipeline.publish import KnownPublishError


class IncrementCurrentFile(pyblish.api.ContextPlugin):
    """Increment the current file.

    Saves the current scene with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["houdini"]
    families = ["workfile",
                "redshift_rop",
                "arnold_rop",
                "mantra_rop",
                "karma_rop",
                "usdrender",
                "publish.hou"]
    optional = True

    def process(self, context):

        errored_plugins = get_errored_plugins_from_context(context)
        if any(
            plugin.__name__ == "HoudiniSubmitPublishDeadline"
            for plugin in errored_plugins
        ):
            raise KnownPublishError(
                "Skipping incrementing current file because "
                "submission to deadline failed."
            )

        # Filename must not have changed since collecting
        host = registered_host()  # type: HoudiniHost
        current_file = host.current_file()
        if context.data["currentFile"] != current_file:
            raise KnownPublishError(
                "Collected filename mismatches from current scene name."
            )

        new_filepath = version_up(current_file)
        host.save_workfile(new_filepath)
