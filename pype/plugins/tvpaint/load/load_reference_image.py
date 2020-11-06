from avalon.vendor import qargparse
from avalon.tvpaint import lib, pipeline


class LoadImage(pipeline.Loader):
    """Load image or image sequence to TVPaint as new layer."""

    families = ["render", "image", "background", "plate"]
    representations = ["*"]

    label = "Load Image"
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

    options = [
        qargparse.Boolean(
            "stretch",
            label="Stretch to project size",
            default=True,
            help="Stretch loaded image/s to project resolution?"
        ),
        qargparse.Boolean(
            "timestretch",
            label="Stretch to timeline length",
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
        subset_name = context["subset"]["name"]
        layer_name = self.get_unique_layer_name(asset_name, subset_name)

        # Fill import script with filename and layer name
        # - filename mus not contain backwards slashes
        george_script = self.import_script.format(
            self.fname.replace("\\", "/"),
            layer_name,
            load_options_str
        )

        lib.execute_george_through_file(george_script)

        loaded_layer = None
        layers = lib.layers_data()
        for layer in layers:
            if layer["name"] == layer_name:
                loaded_layer = layer
                break

        if loaded_layer is None:
            raise AssertionError(
                "Loading probably failed during execution of george script."
            )

        layer_ids = [loaded_layer["layer_id"]]
        namespace = namespace or layer_name
        return pipeline.containerise(
            name=name,
            namespace=namespace,
            layer_ids=layer_ids,
            context=context,
            loader=self.__class__.__name__
        )

    def _remove_layers(self, layer_ids, layers=None):
        if not layer_ids:
            return

        if layers is None:
            layers = lib.layers_data()

        available_ids = set(layer["layer_id"] for layer in layers)
        layer_ids_to_remove = []

        for layer_id in layer_ids:
            if layer_id in available_ids:
                layer_ids_to_remove.append(layer_id)

        if not layer_ids_to_remove:
            return

        george_script_lines = []
        for layer_id in layer_ids_to_remove:
            line = "tv_layerkill {}".format(layer_id)
            george_script_lines.append(line)
        george_script = "\n".join(george_script_lines)
        lib.execute_george_through_file(george_script)

    def remove(self, container):
        layer_ids = self.layer_ids_from_container(container)
        self._remove_layers(layer_ids)

        current_containers = pipeline.ls()
        pop_idx = None
        for idx, cur_con in enumerate(current_containers):
            if cur_con["objectName"] == container["objectName"]:
                pop_idx = idx
                break

        if pop_idx is None:
            self.log.warning(
                "Didn't found container in workfile containers. {}".format(
                    container
                )
            )
            return

        current_containers.pop(pop_idx)
        pipeline.write_workfile_metadata(
            pipeline.SECTION_NAME_CONTAINERS, current_containers
        )

