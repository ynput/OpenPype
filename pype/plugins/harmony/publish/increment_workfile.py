import os

import pyblish.api
from pype.action import get_errored_plugins_from_data
from pype.lib import version_up
from avalon import harmony


class IncrementWorkfile(pyblish.api.InstancePlugin):
    """Increment the current workfile.

    Saves the current scene with an increased version number.
    """

    label = "Increment Workfile"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["harmony"]
    families = ["workfile"]
    optional = True

    def process(self, instance):
        errored_plugins = get_errored_plugins_from_data(instance.context)
        if errored_plugins:
            raise RuntimeError(
                "Skipping incrementing current file because publishing failed."
            )

        scene_dir = version_up(
            os.path.dirname(instance.context.data["currentFile"])
        )
        scene_path = os.path.join(
            scene_dir, os.path.basename(scene_dir) + ".xstage"
        )

        harmony.save_scene_as(scene_path)

        self.log.info("Incremented workfile to: {}".format(scene_path))
