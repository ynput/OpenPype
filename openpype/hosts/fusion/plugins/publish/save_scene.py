import pyblish.api


class FusionSaveComp(pyblish.api.ContextPlugin):
    """Save current comp"""

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["fusion"]
    families = ["render", "image", "workfile"]

    def process(self, context):

        comp = context.data.get("currentComp")
        assert comp, "Must have comp"

        current = comp.GetAttrs().get("COMPS_FileName", "")
        assert context.data['currentFile'] == current

        self.log.info("Saving current file: {}".format(current))
        comp.Save()
