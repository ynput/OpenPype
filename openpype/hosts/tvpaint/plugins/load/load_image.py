from openpype.lib.attribute_definitions import BoolDef
from openpype.hosts.tvpaint.api import plugin
from openpype.hosts.tvpaint.api.lib import execute_george_through_file


class ImportImage(plugin.Loader):
    """Load image or image sequence to TVPaint as new layer."""

    families = ["render", "image", "background", "plate", "review"]
    representations = ["*"]

    label = "Import Image"
    order = 1
    icon = "image"
    color = "white"

    import_script = (
        "filepath = \"{}\"\n"
        "layer_name = \"{}\"\n"
        "tv_loadsequence filepath {}PARSE layer_id\n"
        "tv_layerrename layer_id layer_name"
    )

    defaults = {
        "stretch": True,
        "timestretch": True,
        "preload": True
    }

    @classmethod
    def get_options(cls, contexts):
        return [
            BoolDef(
                "stretch",
                label="Stretch to project size",
                default=cls.defaults["stretch"],
                tooltip="Stretch loaded image/s to project resolution?"
            ),
            BoolDef(
                "timestretch",
                label="Stretch to timeline length",
                default=cls.defaults["timestretch"],
                tooltip="Clip loaded image/s to timeline length?"
            ),
            BoolDef(
                "preload",
                label="Preload loaded image/s",
                default=cls.defaults["preload"],
                tooltip="Preload image/s?"
            )
        ]

    def load(self, context, name, namespace, options):
        stretch = options.get("stretch", self.defaults["stretch"])
        timestretch = options.get("timestretch", self.defaults["timestretch"])
        preload = options.get("preload", self.defaults["preload"])

        load_options = []
        if stretch:
            load_options.append("\"STRETCH\"")
        if timestretch:
            load_options.append("\"TIMESTRETCH\"")
        if preload:
            load_options.append("\"PRELOAD\"")

        load_options_str = ""
        for load_option in load_options:
            load_options_str += (load_option + " ")

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
        path = self.filepath_from_context(context).replace("\\", "/")
        george_script = self.import_script.format(
            path,
            layer_name,
            load_options_str
        )
        return execute_george_through_file(george_script)
