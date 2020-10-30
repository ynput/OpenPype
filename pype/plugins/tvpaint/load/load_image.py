from avalon import api
from avalon.vendor import qargparse
from avalon.tvpaint import CommunicatorWrapper


class ImportImage(api.Loader):
    """Load image or image sequence to TVPaint as new layer."""

    families = ["render", "image", "background", "plate"]
    representations = ["*"]

    label = "Import Image"
    order = 1
    icon = "image"
    color = "white"

    import_script = (
        "filepath = \"{}\"\n"
        "layer_name = \"{}\"\n"
        "tv_loadsequence filepath \"preload\" PARSE layer_id\n"
        "tv_layerrename layer_id layer_name"
    )

    options = [
        qargparse.Boolean(
            "stretch",
            label="Stretch to project size",
            default=True,
            help="Stretch loaded image/s to project resolution?"
        ),
        qargparse.Boolean(
            "timestretch",
            label=" Stretch to timeline length",
            default=True,
            help="Clip loaded image/s to timeline length?"
        ),
        qargparse.Boolean(
            "preload",
            label="Preload loaded image/s",
            default=True,
            help="Preload image/s?"
        )
    ]

    def load(self, context, name, namespace, options):
        # Prepare layer name
        asset_name = context["asset"]["name"]
        version_name = context["version"]["name"]
        layer_name = "{}_{}_v{:0>3}".format(
            asset_name,
            name,
            version_name
        )
        # Fill import script with filename and layer name
        # - filename mus not contain backwards slashes
        george_script = self.import_script.format(
            self.fname.replace("\\", "/"),
            layer_name
        )
        return CommunicatorWrapper.execute_george_through_file(george_script)
