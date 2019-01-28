import pyblish.api


class IncrementCurrentFileDeadline(pyblish.api.ContextPlugin):
    """Increment the current file.

    Saves the current maya scene with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["maya"]
    families = ["colorbleed.renderlayer",
                "colorbleed.vrayscene"]
    optional = True

    def process(self, context):

        import os
        from maya import cmds
        from colorbleed.lib import version_up
        from colorbleed.action import get_errored_plugins_from_data

        errored_plugins = get_errored_plugins_from_data(context)
        if any(plugin.__name__ == "MayaSubmitDeadline"
                for plugin in errored_plugins):
            raise RuntimeError("Skipping incrementing current file because "
                               "submission to deadline failed.")

        current_filepath = context.data["currentFile"]
        new_filepath = version_up(current_filepath)

        # Ensure the suffix is .ma because we're saving to `mayaAscii` type
        if not new_filepath.endswith(".ma"):
            self.log.warning("Refactoring scene to .ma extension")
            new_filepath = os.path.splitext(new_filepath)[0] + ".ma"

        cmds.file(rename=new_filepath)
        cmds.file(save=True, force=True, type="mayaAscii")
