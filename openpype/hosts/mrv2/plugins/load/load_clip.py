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

        # Match publish fps if mrv2 supports `setSpeed` (0.8+)
        if hasattr(cmd, "setSpeed"):
            fps = self.get_fps(context)
            cmd.setSpeed(fps)

    def get_fps(self, context, default=25):
        for entity in ["representation", "version", "asset", "project"]:
            fps = context[entity].get("data", {}).get("fps")
            if fps is not None:
                self.log.info(f"Using FPS from {entity}: {fps}")
                return fps

        self.log.warning(f"Using fallback default FPS: {fps}")
        return default
