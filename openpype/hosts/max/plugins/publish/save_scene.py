import pyblish.api
import os


class SaveCurrentScene(pyblish.api.ContextPlugin):
    """Save current scene

    """

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["max"]
    families = ["maxrender", "workfile"]

    def process(self, context):
        from pymxs import runtime as rt
        folder = rt.maxFilePath
        file = rt.maxFileName
        current = os.path.join(folder, file)
        assert context.data["currentFile"] == current
        rt.saveMaxFile(current)
