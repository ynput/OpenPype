import os
import re

import pyblish.api

from openpype.pipeline import publish


class ExtractGafferSceneWriter(
    publish.Extractor,
    publish.OpenPypePyblishPluginMixin
):
    """Export Gaffer Scene Writer"""

    order = pyblish.api.ExtractorOrder
    label = "Gaffer Scene Writer"
    hosts = ["gaffer"]
    families = ["pointcache"]

    def process(self, instance):

        node = instance.data["transientData"]["node"]

        filepath = node["fileName"].getValue()

        if "#" in filepath:
            # Replace hash tokens (#) with frame number
            context = node.scriptNode().context()
            frame = context.getFrame()

            def fn(match):
                padding = len(match.group(0))
                return str(frame).zfill(padding)

            filepath = re.sub("(#+)", fn, filepath)

        # Export node
        # TODO: Support `executeSequence(frames: List[int])` to render sequence
        node.execute()

        # Add representation to instance
        ext = os.path.splitext(filepath)[-1].strip(".")
        representation = {
            "name": ext,
            "ext": ext,
            "files": os.path.basename(filepath),
            "stagingDir": os.path.dirname(filepath),
        }
        representations = instance.data.setdefault("representations", [])
        representations.append(representation)
