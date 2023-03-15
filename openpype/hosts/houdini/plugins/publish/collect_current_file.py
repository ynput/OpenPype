import os
import hou

from openpype.pipeline import legacy_io
import pyblish.api


class CollectHoudiniCurrentFile(pyblish.api.InstancePlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.01
    label = "Houdini Current File"
    hosts = ["houdini"]
    family = ["workfile"]

    def process(self, instance):
        """Inject the current working file"""

        current_file = hou.hipFile.path()
        if not os.path.exists(current_file):
            # By default, Houdini will even point a new scene to a path.
            # However if the file is not saved at all and does not exist,
            # we assume the user never set it.
            filepath = ""

        elif os.path.basename(current_file) == "untitled.hip":
            # Due to even a new file being called 'untitled.hip' we are unable
            # to confirm the current scene was ever saved because the file
            # could have existed already. We will allow it if the file exists,
            # but show a warning for this edge case to clarify the potential
            # false positive.
            self.log.warning(
                "Current file is 'untitled.hip' and we are "
                "unable to detect whether the current scene is "
                "saved correctly."
            )

        instance.context.data["currentFile"] = current_file

        folder, file = os.path.split(current_file)
        filename, ext = os.path.splitext(file)

        instance.data.update({
            "setMembers": [current_file],
            "frameStart": instance.context.data['frameStart'],
            "frameEnd": instance.context.data['frameEnd'],
            "handleStart": instance.context.data['handleStart'],
            "handleEnd": instance.context.data['handleEnd']
        })

        instance.data['representations'] = [{
            'name': ext.lstrip("."),
            'ext': ext.lstrip("."),
            'files': file,
            "stagingDir": folder,
        }]

        self.log.info('Collected instance: {}'.format(file))
        self.log.info('Scene path: {}'.format(current_file))
        self.log.info('staging Dir: {}'.format(folder))
