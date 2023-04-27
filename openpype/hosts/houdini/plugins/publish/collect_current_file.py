import os
import hou

import pyblish.api


class CollectHoudiniCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Houdini Current File"
    hosts = ["houdini"]

    def process(self, context):
        """Inject the current working file"""

        current_file = hou.hipFile.path()
        if not os.path.exists(current_file):
            # By default, Houdini will even point a new scene to a path.
            # However if the file is not saved at all and does not exist,
            # we assume the user never set it.
            current_file = ""

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

        context.data["currentFile"] = current_file
        self.log.info('Current workfile path: {}'.format(current_file))
