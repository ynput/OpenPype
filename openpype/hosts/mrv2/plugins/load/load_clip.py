import openpype.pipeline.load as load
from openpype.lib.transcoding import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


class LoadClip(load.LoaderPlugin):
    """Load movie or sequence into MRV2"""

    families = [
        "imagesequence",
        "review",
        "render",
        "plate",
        "image",
        "online",
    ]
    representations = ["*"]
    extensions = set(
        ext.lstrip(".") for ext in IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)
    )

    label = "Load clip"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        path = self.filepath_from_context(context)

        from mrv2 import cmd
        cmd.open(path)
