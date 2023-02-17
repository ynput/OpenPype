import pyblish.api

from openpype.lib import version_up
from openpype.pipeline import registered_host
from openpype.hosts.houdini.api import HoudiniHost

class IncrementCurrentFile(pyblish.api.ContextPlugin):
    """Increment the current file.

    Saves the current scene with an increased version number.

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["houdini"]
    families = ["workfile"]
    optional = True

    def process(self, context):

        # Filename must not have changed since collecting
        host = registered_host()  # type: HoudiniHost
        current_file = host.current_file()
        assert (
            context.data["currentFile"] == current_file
        ), "Collected filename from current scene name."

        new_filepath = version_up(current_file)
        host.save_workfile(new_filepath)
