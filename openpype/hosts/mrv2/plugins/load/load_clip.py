import os

import openpype.pipeline.load as load
from openpype.lib.transcoding import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from openpype.lib import BoolDef


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

    options = [
        BoolDef(
            "setFps",
            label="Set FPS",
            default=True,
            tooltip=(
                "Set the FPS of the representation, version, asset or project "
                "related to the loaded file.\n"
                "Use whichever has 'data.fps' defined first."
            )
        ),
        BoolDef(
            "setColorspace",
            label="Set Colorspace",
            default=True,
            tooltip=(
                "Set the colorspace of the representation if it has any "
                "colorspace information."
            )
        )
    ]

    def load(self, context, name, namespace, data):

        from mrv2 import cmd, timeline

        path = self.filepath_from_context(context)
        cmd.open(path)

        # Match publish fps
        if data.get("setFps", True):
            fps = self.get_fps(context)
            timeline.setSpeed(fps)

        # Match publish colorspace
        if data.get("setColorspace", True):
            colorspace_data = self.get_colorspace_data(context)
            if colorspace_data:
                self.set_colorspace(colorspace_data)

    def set_colorspace(self, colorspace_data):

        from mrv2 import image

        # TODO: The path should actually be retrieved through template
        config_path = colorspace_data["config"]["path"]
        if os.path.exists(config_path):

            image.setOcioConfig(config_path)
            image.setOcioIcs(colorspace_data["colorspace"])
            # TODO: Should we also set display `colorspace_data["display"]`?
            image.setOcioView(colorspace_data["view"])
        else:
            self.log.warning(
                "OCIO Colorspace data found for file, but OCIO config "
                f"path not found on disk: {config_path}. "
                "Ignoring colorspace data."
            )

    def get_fps(self, context, default=25):
        for entity in ["representation", "version", "asset", "project"]:
            fps = context[entity].get("data", {}).get("fps")
            if fps is not None:
                self.log.info(f"Using FPS from '{entity}': {fps}")
                return fps

        self.log.warning(f"Using fallback default FPS: {fps}")
        return default

    def get_colorspace_data(self, context):
        """Return colorspace of the file to load.

        Retrieves the explicit colorspace from the publish.

        Returns:
            dict or None: The colorspace data or None if not detected.

        """
        representation = context["representation"]
        colorspace_data = representation.get("data", {}).get("colorspaceData")
        if colorspace_data:
            # Example data:
            # "colorspaceData": {
            #     "colorspace": "ACEScg",
            #     "config": {
            #         "path": "/path/to/config.ocio",
            #         "template": "{template}/to/config.ocio"
            #     },
            #     "display": "sRGB",
            #     "view": "ACES 1.0 SDR-video"
            # },
            return colorspace_data
