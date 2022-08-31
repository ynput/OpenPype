import pyblish.api

import hou
from openpype.lib import version_up
from openpype.pipeline.publish import get_errored_plugins_from_context


class IncrementCurrentFileDeadline(pyblish.api.ContextPlugin):
    """Increment the current file.

    Saves the current scene with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["houdini"]
    targets = ["deadline"]

    def process(self, context):

        errored_plugins = get_errored_plugins_from_context(context)
        if any(
            plugin.__name__ == "HoudiniSubmitPublishDeadline"
            for plugin in errored_plugins
        ):
            raise RuntimeError(
                "Skipping incrementing current file because "
                "submission to deadline failed."
            )

        current_filepath = context.data["currentFile"]
        new_filepath = version_up(current_filepath)

        hou.hipFile.save(file_name=new_filepath, save_to_recent_files=True)
