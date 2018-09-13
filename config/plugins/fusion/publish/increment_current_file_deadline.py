import pyblish.api


class FusionIncrementCurrentFile(pyblish.api.ContextPlugin):
    """Increment the current file.

    Saves the current file with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["fusion"]
    families = ["colorbleed.saver.deadline"]
    optional = True

    def process(self, context):

        from colorbleed.lib import version_up
        from colorbleed.action import get_errored_plugins_from_data

        errored_plugins = get_errored_plugins_from_data(context)
        if any(plugin.__name__ == "FusionSubmitDeadline"
                for plugin in errored_plugins):
            raise RuntimeError("Skipping incrementing current file because "
                               "submission to deadline failed.")

        comp = context.data.get("currentComp")
        assert comp, "Must have comp"

        current_filepath = context.data["currentFile"]
        new_filepath = version_up(current_filepath)

        comp.Save(new_filepath)
