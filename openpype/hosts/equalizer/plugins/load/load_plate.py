import contextlib

import openpype.pipeline.load as load
from openpype.pipeline.load import get_representation_context
from openpype.lib.transcoding import IMAGE_EXTENSIONS


class LoadPlate(load.LoaderPlugin):
    families = [
        "imagesequence",
        "review",
        "render",
        "plate",
        "image",
        "online",
    ]

    representations = ["*"]
    extensions = {ext.lstrip(".") for ext in IMAGE_EXTENSIONS}

    label = "Load sequence"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        if namespace is None:
            namespace = context["asset"]["name"]

            # Use the first file for now
            path = self.filepath_from_context(context)
            self.log.info(f"Loading: {path}")
