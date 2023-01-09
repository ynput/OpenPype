import pyblish.api


class IncrementCurrentFileDeadline(pyblish.api.ContextPlugin):
    """Increment the current file.

    Saves the current maya scene with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["maya"]
    families = ["workfile"]
    optional = True

    def process(self, context):

        from maya import cmds
        from openpype.lib import version_up
        from openpype.pipeline.publish import get_errored_plugins_from_context

        errored_plugins = get_errored_plugins_from_context(context)
        if any(plugin.__name__ == "MayaSubmitDeadline"
                for plugin in errored_plugins):
            raise RuntimeError("Skipping incrementing current file because "
                               "submission to deadline failed.")

        current_filepath = context.data["currentFile"]
        new_filepath = version_up(current_filepath)

        # # Ensure the suffix is .ma because we're saving to `mayaAscii` type
        if new_filepath.endswith(".ma"):
            fileType = "mayaAscii"
        elif new_filepath.endswith(".mb"):
            fileType = "mayaBinary"

        cmds.file(rename=new_filepath)
        cmds.file(save=True, force=True, type=fileType)
