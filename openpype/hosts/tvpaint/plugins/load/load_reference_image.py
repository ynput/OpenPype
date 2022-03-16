import collections
import qargparse
from avalon.pipeline import get_representation_context
from openpype.hosts.tvpaint.api import lib, pipeline, plugin


class LoadImage(plugin.Loader):
    """Load image or image sequence to TVPaint as new layer."""

    families = ["render", "image", "background", "plate", "review"]
    representations = ["*"]

    label = "Load Image"
    order = 1
    icon = "image"
    color = "white"

    import_script = (
        "filepath = '\"'\"{}\"'\"'\n"
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

        layer_names = [loaded_layer["name"]]
        namespace = namespace or layer_name
        return pipeline.containerise(
            name=name,
            namespace=namespace,
            members=layer_names,
            context=context,
            loader=self.__class__.__name__
        )

    def _remove_layers(self, layer_names=None, layer_ids=None, layers=None):
        if not layer_names and not layer_ids:
            self.log.warning("Got empty layer names list.")
            return

        if layers is None:
            layers = lib.layers_data()

        available_ids = set(layer["layer_id"] for layer in layers)

        if layer_ids is None:
            # Backwards compatibility (layer ids were stored instead of names)
            layer_names_are_ids = True
            for layer_name in layer_names:
                if (
                    not isinstance(layer_name, int)
                    and not layer_name.isnumeric()
                ):
                    layer_names_are_ids = False
                    break

            if layer_names_are_ids:
                layer_ids = layer_names

        layer_ids_to_remove = []
        if layer_ids is not None:
            for layer_id in layer_ids:
                if layer_id in available_ids:
                    layer_ids_to_remove.append(layer_id)

        else:
            layers_by_name = collections.defaultdict(list)
            for layer in layers:
                layers_by_name[layer["name"]].append(layer)

            for layer_name in layer_names:
                layers = layers_by_name[layer_name]
                if len(layers) == 1:
                    layer_ids_to_remove.append(layers[0]["layer_id"])

        if not layer_ids_to_remove:
            self.log.warning("No layers to delete.")
            return

        george_script_lines = []
        for layer_id in layer_ids_to_remove:
            line = "tv_layerkill {}".format(layer_id)
            george_script_lines.append(line)
        george_script = "\n".join(george_script_lines)
        lib.execute_george_through_file(george_script)

    def _remove_container(self, container, members=None):
        if not container:
            return
        representation = container["representation"]
        members = self.get_members_from_container(container)
        current_containers = pipeline.ls()
        pop_idx = None
        for idx, cur_con in enumerate(current_containers):
            cur_members = self.get_members_from_container(cur_con)
            if (
                cur_members == members
                and cur_con["representation"] == representation
            ):
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

    def remove(self, container):
        members = self.get_members_from_container(container)
        self.log.warning("Layers to delete {}".format(members))
        self._remove_layers(members)
        self._remove_container(container)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """Replace container with different version.

        New layers are loaded as first step. Then is tried to change data in
        new layers with data from old layers. When that is done old layers are
        removed.
        """
        # Create new containers first
        context = get_representation_context(representation)

        # Get layer ids from previous container
        old_layer_names = self.get_members_from_container(container)

        # Backwards compatibility (layer ids were stored instead of names)
        old_layers_are_ids = True
        for name in old_layer_names:
            if isinstance(name, int) or name.isnumeric():
                continue
            old_layers_are_ids = False
            break

        old_layers = []
        layers = lib.layers_data()
        previous_layer_ids = set(layer["layer_id"] for layer in layers)
        if old_layers_are_ids:
            for layer in layers:
                if layer["layer_id"] in old_layer_names:
                    old_layers.append(layer)
        else:
            layers_by_name = collections.defaultdict(list)
            for layer in layers:
                layers_by_name[layer["name"]].append(layer)

            for layer_name in old_layer_names:
                layers = layers_by_name[layer_name]
                if len(layers) == 1:
                    old_layers.append(layers[0])

        # Prepare few data
        new_start_position = None
        new_group_id = None
        layer_ids_to_remove = set()
        for layer in old_layers:
            layer_ids_to_remove.add(layer["layer_id"])
            position = layer["position"]
            group_id = layer["group_id"]
            if new_start_position is None:
                new_start_position = position
            elif new_start_position > position:
                new_start_position = position

            if new_group_id is None:
                new_group_id = group_id
            elif new_group_id < 0:
                continue
            elif new_group_id != group_id:
                new_group_id = -1

        # Remove old container
        self._remove_container(container)
        # Remove old layers
        self._remove_layers(layer_ids=layer_ids_to_remove)

        # Change `fname` to new representation
        self.fname = self.filepath_from_context(context)

        name = container["name"]
        namespace = container["namespace"]
        new_container = self.load(context, name, namespace, {})
        new_layer_names = self.get_members_from_container(new_container)

        layers = lib.layers_data()

        new_layers = []
        for layer in layers:
            if layer["layer_id"] in previous_layer_ids:
                continue
            if layer["name"] in new_layer_names:
                new_layers.append(layer)

        george_script_lines = []
        # Group new layers to same group as previous container layers had
        # - all old layers must be under same group
        if new_group_id is not None and new_group_id > 0:
            for layer in new_layers:
                line = "tv_layercolor \"set\" {} {}".format(
                    layer["layer_id"], new_group_id
                )
                george_script_lines.append(line)

        # Rename new layer to have same name
        # - only if both old and new have one layer
        if len(old_layers) == 1 and len(new_layers) == 1:
            layer_name = old_layers[0]["name"]
            george_script_lines.append(
                "tv_layerrename {} \"{}\"".format(
                    new_layers[0]["layer_id"], layer_name
                )
            )

        # Change position of new layer
        # - this must be done before remove old layers
        if len(new_layers) == 1 and new_start_position is not None:
            new_layer = new_layers[0]
            george_script_lines.extend([
                "tv_layerset {}".format(new_layer["layer_id"]),
                "tv_layermove {}".format(new_start_position)
            ])

        # Execute george scripts if there are any
        if george_script_lines:
            george_script = "\n".join(george_script_lines)
            lib.execute_george_through_file(george_script)
