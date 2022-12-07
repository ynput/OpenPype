import pyblish.api

from openpype.lib import version_up
from openpype.pipeline import registered_host
from openpype.action import get_errored_plugins_from_data
from openpype.hosts.houdini.api import HoudiniHost

class IncrementCurrentFile(pyblish.api.ContextPlugin):
    """Increment the current file.

    Saves the current scene with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["houdini"]
    families = ["workfile", "redshift_rop", "arnold_rop", "usdrender"]
    optional = True

    def process(self, instance):

        # This should be a ContextPlugin, but this is a workaround
        # for a bug in pyblish to run once for a family: issue #250
        context = instance.context
        key = "__hasRun{}".format(self.__class__.__name__)
        if context.data.get(key, False):
            return
        else:
            context.data[key] = True

        context = instance.context
        errored_plugins = get_errored_plugins_from_data(context)
        if any(
            plugin.__name__ == "HoudiniSubmitPublishDeadline"
            for plugin in errored_plugins
        ):
            raise RuntimeError(
                "Skipping incrementing current file because "
                "submission to deadline failed."
            )

        # Filename must not have changed since collecting
        host = registered_host()  # type: HoudiniHost
        current_file = host.current_file()
        assert (
            context.data["currentFile"] == current_file
        ), "Collected filename from current scene name."

        new_filepath = version_up(current_file)
        host.save_workfile(new_filepath)
