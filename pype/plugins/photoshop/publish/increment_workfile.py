import pyblish.api
from pype.action import get_errored_plugins_from_data
from pype.lib import version_up

from avalon import photoshop


class IncrementWorkfile(pyblish.api.InstancePlugin):
    """Increment the current workfile.

    Saves the current scene with an increased version number.
    """

    label = "Increment Workfile"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["photoshop"]
    families = ["workfile"]
    optional = True

    def process(self, instance):
        errored_plugins = get_errored_plugins_from_data(instance.context)
        if errored_plugins:
            raise RuntimeError(
                "Skipping incrementing current file because publishing failed."
            )

        scene_path = version_up(instance.context.data["currentFile"])
        photoshop.stub().saveAs(scene_path, 'psd', True)

        self.log.info("Incremented workfile to: {}".format(scene_path))
