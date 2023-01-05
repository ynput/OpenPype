import os
import hou

import pyblish.api


class CollectHoudiniCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Houdini Current File"
    hosts = ["houdini"]

    def process(self, context):
        """Inject the current working file"""

        filepath = hou.hipFile.path()
        if not os.path.exists(filepath):
            # By default Houdini will even point a new scene to a path.
            # However if the file is not saved at all and does not exist,
            # we assume the user never set it.
            filepath = ""

        elif os.path.basename(filepath) == "untitled.hip":
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

        context.data["currentFile"] = filepath
