import pyblish.api


class ValidateCurrentSaveFile(pyblish.api.ContextPlugin):
    """File must be saved before publishing"""

    label = "Validate File Saved"
    order = pyblish.api.ValidatorOrder - 0.1
    hosts = ["maya", "houdini", "nuke"]

    def process(self, context):

        current_file = context.data["currentFile"]
        if not current_file:
            raise RuntimeError("File not saved")
