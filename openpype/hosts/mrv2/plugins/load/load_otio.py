import openpype.pipeline.load as load


class LoadOtio(load.LoaderPlugin):
    """Load movie or sequence into MRV2"""

    families = ["*"]
    representations = ["*"]
    extensions = {"otio"}

    label = "Load OTIO timeline"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        path = self.filepath_from_context(context)

        from mrv2 import cmd
        cmd.open(path)
