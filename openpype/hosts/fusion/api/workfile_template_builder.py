from openpype.pipeline import registered_host
from openpype.pipeline.workfile.workfile_template_builder import (
    AbstractTemplateBuilder,
    PlaceholderPlugin,
    LoadPlaceholderItem,
    CreatePlaceholderItem,
    PlaceholderLoadMixin,
    PlaceholderCreateMixin,
)
from openpype.tools.workfile_template_build import (
    WorkfileBuildPlaceholderDialog,
)

from .lib import (
    get_current_comp,
    get_bmd_library,
    get_names_from_nodes,
)

PLACEHOLDER_SET = "PLACEHOLDERS_SET"


class FusionTemplateBuilder(AbstractTemplateBuilder):
    """Concrete implementation of AbstractTemplateBuilder for Fusion"""

    def import_template(self, path):
        """Import template into current scene.
        Block if a template is already loaded.

        Args:
            path (str): A path to current template (usually given by
            get_template_preset implementation)

        Returns:
            bool: Wether the template was successfully imported or not
        """

        bmd = get_bmd_library()
        comp = get_current_comp()
        comp.Paste(bmd.readfile(path))

        # Make sure no node is selected before starting to process the comp
        flow = comp.CurrentFrame.FlowView
        flow.Select()
        return True


class FusionPlaceholderPlugin(PlaceholderPlugin):
    node_color = {
        "R": 0.26666666666666666,
        "G": 0.5607843137254902,
        "B": 0.396078431372549,
    }  # Green

    def _collect_scene_placeholders(self):
        # Cache placeholder data to shared data
        placeholder_nodes = self.builder.get_shared_populate_data(
            "placeholder_nodes"
        )

        if placeholder_nodes is None:
            comp = get_current_comp()
            placeholder_nodes = list(
                comp.GetToolList(False, "Fuse.OPEmpty").values()
            )
            self.builder.set_shared_populate_data(
                "placeholder_nodes", placeholder_nodes
            )

        return placeholder_nodes

    def create_placeholder(self, placeholder_data):
        placeholder_data["plugin_identifier"] = self.identifier

        comp = get_current_comp()
        node = comp.AddTool("Fuse.OPEmpty", -32768, -32768)
        node = self._populate_controls(node, placeholder_data)

        node.SetAttrs({"TOOLS_Name": "PLACEHOLDER"})
        node.TileColor = self.node_color

        node.SetData("placeholder_data", {})
        node.SetData("is_placeholder", True)

    def update_placeholder(self, placeholder_item, new_placeholder_data):
        comp = get_current_comp()
        node = comp.FindTool(placeholder_item.scene_identifier)
        for name, data in new_placeholder_data.items():
            if node[name] is not None:
                node[name] = data
            else:
                raise KeyError(f"Control {name} does not exist on the node")

        placeholder_data = node.GetData("placeholder_data")
        placeholder_data.update(new_placeholder_data)
        node.SetData("placeholder_data", placeholder_data)

    def _is_float(self, element):
        try:
            float(element)
            return float(element)
        except ValueError:
            return element

    def _parse_placeholder_node_data(self, node):
        placeholder_data = {}
        attrs = node.UserControls
        for id in attrs.keys():
            placeholder_data[id] = self._is_float(node[id][0])

        return placeholder_data

    def _populate_controls(self, node, placeholder_data):
        """Pupulate the node with text controls contaning the data"""
        controls = node.UserControls

        for name, data in placeholder_data.items():
            controls[name] = {
                "LINKS_Name": name,
                "LINKID_DataType": "Text",
                "INPID_InputControl": "TextEditControl",
                "TEC_Lines": 1,
                "INP_External": False,
                "ICS_ControlPage": "Controls",
                "INPS_DefaultText": data,
            }

        node.UserControls = controls
        node = node.Refresh()

        return node


class FusionPlaceholderLoadPlugin(
    FusionPlaceholderPlugin, PlaceholderLoadMixin
):
    identifier = "fusion.load"
    label = "Fusion load"

    def _parse_placeholder_node_data(self, node):
        node_data = super(
            FusionPlaceholderLoadPlugin, self
        )._parse_placeholder_node_data(node)

        placeholder_data = node.GetData("placeholder_data")
        nb_children = 0
        if "nb_children" in placeholder_data:
            nb_children = int(placeholder_data["nb_children"])
        node_data["nb_children"] = nb_children

        siblings = []
        if "siblings" in placeholder_data:
            siblings = placeholder_data["siblings"]
        node_data["siblings"] = siblings

        node_full_name = node.Name
        node_data["group_name"] = node_full_name.rpartition(".")[0]
        node_data["last_loaded"] = []
        node_data["delete"] = False
        return node_data

    def _get_loaded_repre_ids(self):
        loaded_representation_ids = self.builder.get_shared_populate_data(
            "loaded_representation_ids"
        )
        if loaded_representation_ids is None:
            loaded_representation_ids = set()
            comp = get_current_comp()
            for node in comp.GetToolList(False, "Fuse.OPEmpty").values():
                if node.GetData("repre_id") is not None:
                    loaded_representation_ids.add(node.GetData("repre_id"))

            self.builder.set_shared_populate_data(
                "loaded_representation_ids", loaded_representation_ids
            )
        return loaded_representation_ids

    def _before_repre_load(self, placeholder, representation):
        comp = get_current_comp()
        nodes_init = []
        for node in comp.GetToolList().values():
            nodes_init.append(node.Name)
        placeholder.data["nodes_init"] = list(nodes_init)
        placeholder.data["last_repre_id"] = str(representation["_id"])

    def collect_placeholders(self):
        output = []
        scene_placeholders = self._collect_scene_placeholders()
        for node in scene_placeholders:
            node_name = node.Name
            plugin_identifier = node["plugin_identifier"][0]
            if (
                plugin_identifier is None
                or plugin_identifier != self.identifier
            ):
                continue

            placeholder_data = self._parse_placeholder_node_data(node)
            output.append(
                LoadPlaceholderItem(node_name, placeholder_data, self)
            )

        return output

    def populate_placeholder(self, placeholder):
        placeholder.data["loader_args"] = "{'x': -32767, 'y': -32767}"
        self.populate_load_placeholder(placeholder)

    def repopulate_placeholder(self, placeholder):
        repre_ids = self._get_loaded_repre_ids()
        self.populate_load_placeholder(placeholder, repre_ids)

    def get_placeholder_options(self, options=None):
        return self.get_load_plugin_options(options)

    def cleanup_placeholder(self, placeholder, failed):
        """
        Move all nodes to correct location,
        do the correct connections and delete template nodes if expected
        """
        comp = get_current_comp()

        # Make sure no node is selected before starting to process
        flow = comp.CurrentFrame.FlowView
        flow.Select()
        placeholder.data["node"] = comp.FindTool(placeholder.scene_identifier)

        # getting the latest nodes added
        nodes_init = placeholder.data["nodes_init"]
        added_nodes = []
        for node in comp.GetToolList().values():
            added_nodes.append(node.Name)
        nodes_loaded_names = list(set(added_nodes) - set(nodes_init))
        nodes_loaded = []
        for name in nodes_loaded_names:
            nodes_loaded.append(comp.FindTool(name))

        self.log.debug("Loaded node: {}".format(nodes_loaded_names))

        if not nodes_loaded:
            return

        placeholder.data["delete"] = True

        placeholder.data["last_loaded"] = nodes_loaded

        if placeholder.data.get("keep_placeholder"):
            self._setdata_siblings(placeholder)

        if placeholder.data["nb_children"] == 0:
            # save initial nodes postions and dimensions, update them
            # and set inputs and outputs of loaded nodes
            self._update_nodes(placeholder.data["node"], nodes_loaded)

            self._set_loaded_connections(placeholder)

        elif placeholder.data["siblings"]:
            # create copies of placeholder siblings for the new loaded nodes,
            # set their inputs and outpus and update all nodes positions and
            # dimensions and siblings names

            # TODO Convert to Fusion:
            """
            siblings = get_nodes_by_names(placeholder.data["siblings"])
            refresh_nodes(siblings)
            copies = self._create_sib_copies(placeholder)
            new_nodes = list(copies.values())  # copies nodes
            self._update_nodes(new_nodes, nodes_loaded)
            placeholder_node.removeKnob(placeholder_node.knob("siblings"))
            new_nodes_name = get_names_from_nodes(new_nodes)
            imprint(placeholder_node, {"siblings": new_nodes_name})
            self._set_copies_connections(placeholder, copies)

            self._update_nodes(nuke.allNodes(), new_nodes + nodes_loaded, 20)

            new_siblings = get_names_from_nodes(new_nodes)
            placeholder.data["siblings"] = new_siblings
            """

        else:
            # if the placeholder doesn't have siblings, the loaded
            # nodes will be placed in a free space

            # TODO Convert to Fusion:
            """
            xpointer, ypointer = find_free_space_to_paste_nodes(
                nodes_loaded, direction="bottom", offset=200
            )
            node = nuke.createNode("NoOp")
            reset_selection()
            nuke.delete(node)
            for node in nodes_loaded:
                xpos = (node.xpos() - min_x) + xpointer
                ypos = (node.ypos() - min_y) + ypointer
                node.setXYpos(xpos, ypos)
            """

        placeholder.data["nb_children"] += 1

        # remove placeholders marked as delete
        if placeholder.data.get("delete") and not placeholder.data.get(
            "keep_placeholder"
        ):
            self.log.debug(
                "Deleting node: {}".format(placeholder.data["node"].Name)
            )
            placeholder.data["node"].Delete()

    def _setdata_siblings(self, placeholder):
        """
        - add siblings names to placeholder attributes (nodes loaded with it)
        - add Id to the attributes of all the other nodes
        """

        loaded_nodes = placeholder.data["last_loaded"]
        loaded_nodes_set = set(loaded_nodes)

        for node in loaded_nodes:
            if node.GetData("builder_type") is None:
                # save the id of representation for all imported nodes
                node.SetData(
                    "repre_id", str(placeholder.data["last_repre_id"])
                )
                continue

            if node.GetData("is_placeholder"):
                siblings = list(loaded_nodes_set - {node})
                siblings_name = get_names_from_nodes(siblings)
                node.SetData("siblings", siblings_name)

    def _update_nodes(self, placeholder_node, nodes):
        """Adjust nodes positions.

        Considering some nodes sizes.

        Args:
            nodes (list): list of nodes to update
        """

        comp = get_current_comp()
        flow = comp.CurrentFrame.FlowView

        x, y = flow.GetPosTable(placeholder_node).values()
        flow.SetPos(placeholder_node, x - 1, y)
        x_offset = 0
        for node in nodes:
            flow.SetPos(node, x + x_offset, y)
            x_offset = x_offset + 1

    def _set_loaded_connections(self, placeholder):
        """
        set inputs and outputs of loaded nodes"""

        # TODO Make it connect to outputs also
        inputs = placeholder.data["node"].Output.GetConnectedInputs().values()
        for input in inputs:
            input.ConnectTo(placeholder.data["last_loaded"][0].Output)

    def _create_sib_copies(self, placeholder):
        """creating copies of the palce_holder siblings (the ones who were
        loaded with it) for the new nodes added

        Returns :
            copies (dict) : with copied nodes names and their copies
        """

        # TODO Convert to Fusion:
        """
        copies = {}
        siblings = get_nodes_by_names(placeholder.data["siblings"])
        for node in siblings:
            new_node = duplicate_node(node)

            x_init = int(new_node.knob("x_init").getValue())
            y_init = int(new_node.knob("y_init").getValue())
            new_node.setXYpos(x_init, y_init)
            if isinstance(new_node, nuke.BackdropNode):
                w_init = new_node.knob("w_init").getValue()
                h_init = new_node.knob("h_init").getValue()
                new_node.knob("bdwidth").setValue(w_init)
                new_node.knob("bdheight").setValue(h_init)
                refresh_node(node)

            if "repre_id" in node.knobs().keys():
                node.removeKnob(node.knob("repre_id"))
            copies[node.name()] = new_node
        return copies
        """
        pass

    def _set_copies_connections(self, placeholder, copies):
        """Set inputs and outputs of the copies.

        Args:
            copies (dict): Copied nodes by their names.
        """

        # TODO Convert to Fusion:
        """
        last_input, last_output = get_group_io_nodes(
            placeholder.data["last_loaded"]
        )
        siblings = get_nodes_by_names(placeholder.data["siblings"])
        siblings_input, siblings_output = get_group_io_nodes(siblings)
        copy_input = copies[siblings_input.name()]
        copy_output = copies[siblings_output.name()]

        for node_init in siblings:
            if node_init == siblings_output:
                continue

            node_copy = copies[node_init.name()]
            for node in node_init.dependent():
                for idx in range(node.inputs()):
                    if node.input(idx) != node_init:
                        continue

                    if node in siblings:
                        copies[node.name()].setInput(idx, node_copy)
                    else:
                        last_input.setInput(0, node_copy)

            for node in node_init.dependencies():
                for idx in range(node_init.inputs()):
                    if node_init.input(idx) != node:
                        continue

                    if node_init == siblings_input:
                        copy_input.setInput(idx, node)
                    elif node in siblings:
                        node_copy.setInput(idx, copies[node.name()])
                    else:
                        node_copy.setInput(idx, last_output)

        siblings_input.setInput(0, copy_output)
        """
        pass


class FusionPlaceholderCreatePlugin(
    FusionPlaceholderPlugin, PlaceholderCreateMixin
):
    identifier = "fusion.create"
    label = "Fusion create"

    def _parse_placeholder_node_data(self, node):
        node_data = super(
            FusionPlaceholderCreatePlugin, self
        )._parse_placeholder_node_data(node)

        placeholder_data = node.GetData("placeholder_data")
        nb_children = 0
        if "nb_children" in placeholder_data:
            nb_children = int(placeholder_data["nb_children"])
        node_data["nb_children"] = nb_children

        siblings = []
        if "siblings" in placeholder_data:
            siblings = placeholder_data["siblings"]
        node_data["siblings"] = siblings

        node_full_name = node.Name
        node_data["group_name"] = node_full_name.rpartition(".")[0]
        node_data["last_loaded"] = []
        node_data["delete"] = False
        return node_data

    def collect_placeholders(self):
        output = []
        scene_placeholders = self._collect_scene_placeholders()
        for node in scene_placeholders:
            node_name = node.Name
            plugin_identifier = node["plugin_identifier"][0]
            if (
                plugin_identifier is None
                or plugin_identifier != self.identifier
            ):
                continue

            placeholder_data = self._parse_placeholder_node_data(node)
            output.append(
                CreatePlaceholderItem(node_name, placeholder_data, self)
            )

        return output

    def populate_placeholder(self, placeholder):
        placeholder.data["loader_args"] = "{'x': -32767, 'y': -32767}"
        self.populate_create_placeholder(placeholder)

    def repopulate_placeholder(self, placeholder):
        self.populate_create_placeholder(placeholder)

    def get_placeholder_options(self, options=None):
        return self.get_create_plugin_options(options)

    def cleanup_placeholder(self, placeholder, failed):
        """
        Move all nodes to correct location,
        do the correct connections and delete template nodes if expected
        """
        comp = get_current_comp()

        # Make sure no node is selected before starting to process
        flow = comp.CurrentFrame.FlowView
        flow.Select()
        placeholder.data["node"] = comp.FindTool(placeholder.scene_identifier)

        # getting the latest nodes added
        nodes_init = placeholder.data["nodes_init"]
        added_nodes = []
        for node in comp.GetToolList().values():
            added_nodes.append(node.Name)
        nodes_created_names = list(set(added_nodes) - set(nodes_init))
        nodes_created = []
        for name in nodes_created_names:
            nodes_created.append(comp.FindTool(name))

        self.log.debug("Created node: {}".format(nodes_created_names))

        if not nodes_created:
            return

        placeholder.data["delete"] = True

        placeholder.data["last_created"] = nodes_created

        if placeholder.data.get("keep_placeholder"):
            self._setdata_siblings(placeholder)

        if placeholder.data["nb_children"] == 0:
            # save initial nodes postions and dimensions, update them
            # and set inputs and outputs of created nodes
            self._update_nodes(placeholder.data["node"], nodes_created)

            self._set_created_connections(placeholder)

        elif placeholder.data["siblings"]:
            # create copies of placeholder siblings for the new created nodes,
            # set their inputs and outpus and update all nodes positions and
            # dimensions and siblings names

            # TODO Convert to Fusion:
            """
            siblings = get_nodes_by_names(placeholder.data["siblings"])
            refresh_nodes(siblings)
            copies = self._create_sib_copies(placeholder)
            new_nodes = list(copies.values())  # copies nodes
            self._update_nodes(new_nodes, nodes_created)
            placeholder_node.removeKnob(placeholder_node.knob("siblings"))
            new_nodes_name = get_names_from_nodes(new_nodes)
            imprint(placeholder_node, {"siblings": new_nodes_name})
            self._set_copies_connections(placeholder, copies)

            self._update_nodes(nuke.allNodes(), new_nodes + nodes_created, 20)

            new_siblings = get_names_from_nodes(new_nodes)
            placeholder.data["siblings"] = new_siblings
            """

        else:
            # if the placeholder doesn't have siblings, the created
            # nodes will be placed in a free space

            # TODO Convert to Fusion:
            """
            xpointer, ypointer = find_free_space_to_paste_nodes(
                nodes_created, direction="bottom", offset=200
            )
            node = nuke.createNode("NoOp")
            reset_selection()
            nuke.delete(node)
            for node in nodes_created:
                xpos = (node.xpos() - min_x) + xpointer
                ypos = (node.ypos() - min_y) + ypointer
                node.setXYpos(xpos, ypos)
            """

        placeholder.data["nb_children"] += 1

        # remove placeholders marked as delete
        if placeholder.data.get("delete") and not placeholder.data.get(
            "keep_placeholder"
        ):
            self.log.debug(
                "Deleting node: {}".format(placeholder.data["node"].Name)
            )
            placeholder.data["node"].Delete()

    def _setdata_siblings(self, placeholder):
        """
        - add siblings names to placeholder attributes (nodes created with it)
        - add Id to the attributes of all the other nodes
        """

        created_nodes = placeholder.data["last_created"]
        created_nodes_set = set(created_nodes)

        for node in created_nodes:
            if node.GetData("is_placeholder"):
                siblings = list(created_nodes_set - {node})
                siblings_name = get_names_from_nodes(siblings)
                node.SetData("siblings", siblings_name)

    def _update_nodes(self, placeholder_node, nodes):
        """Adjust nodes positions.

        Considering some nodes sizes.

        Args:
            nodes (list): list of nodes to update
        """

        comp = get_current_comp()
        flow = comp.CurrentFrame.FlowView

        x, y = flow.GetPosTable(placeholder_node).values()
        flow.SetPos(placeholder_node, x - 1, y)
        x_offset = 0
        for node in nodes:
            flow.SetPos(node, x + x_offset, y)
            x_offset = x_offset + 1

    def _set_created_connections(self, placeholder):
        """
        set inputs and outputs of created nodes"""

        # TODO Make it connect to outputs also
        inputs = placeholder.data["node"].Output.GetConnectedInputs().values()
        for input in inputs:
            input.ConnectTo(placeholder.data["last_created"][0].Output)

    def _create_sib_copies(self, placeholder):
        """creating copies of the palce_holder siblings (the ones who were
        created with it) for the new nodes added

        Returns :
            copies (dict) : with copied nodes names and their copies
        """

        # TODO Convert to Fusion:
        """
        copies = {}
        siblings = get_nodes_by_names(placeholder.data["siblings"])
        for node in siblings:
            new_node = duplicate_node(node)

            x_init = int(new_node.knob("x_init").getValue())
            y_init = int(new_node.knob("y_init").getValue())
            new_node.setXYpos(x_init, y_init)
            if isinstance(new_node, nuke.BackdropNode):
                w_init = new_node.knob("w_init").getValue()
                h_init = new_node.knob("h_init").getValue()
                new_node.knob("bdwidth").setValue(w_init)
                new_node.knob("bdheight").setValue(h_init)
                refresh_node(node)

            if "repre_id" in node.knobs().keys():
                node.removeKnob(node.knob("repre_id"))
            copies[node.name()] = new_node
        return copies
        """
        pass

    def _set_copies_connections(self, placeholder, copies):
        """Set inputs and outputs of the copies.

        Args:
            copies (dict): Copied nodes by their names.
        """

        # TODO Convert to Fusion:
        """
        last_input, last_output = get_group_io_nodes(
            placeholder.data["last_created"]
        )
        siblings = get_nodes_by_names(placeholder.data["siblings"])
        siblings_input, siblings_output = get_group_io_nodes(siblings)
        copy_input = copies[siblings_input.name()]
        copy_output = copies[siblings_output.name()]

        for node_init in siblings:
            if node_init == siblings_output:
                continue

            node_copy = copies[node_init.name()]
            for node in node_init.dependent():
                for idx in range(node.inputs()):
                    if node.input(idx) != node_init:
                        continue

                    if node in siblings:
                        copies[node.name()].setInput(idx, node_copy)
                    else:
                        last_input.setInput(0, node_copy)

            for node in node_init.dependencies():
                for idx in range(node_init.inputs()):
                    if node_init.input(idx) != node:
                        continue

                    if node_init == siblings_input:
                        copy_input.setInput(idx, node)
                    elif node in siblings:
                        node_copy.setInput(idx, copies[node.name()])
                    else:
                        node_copy.setInput(idx, last_output)

        siblings_input.setInput(0, copy_output)
        """
        pass


def build_workfile_template(*args, **kwargs):
    builder = FusionTemplateBuilder(registered_host())
    builder.build_template(*args, **kwargs)


def update_workfile_template(*args):
    builder = FusionTemplateBuilder(registered_host())
    builder.rebuild_template()


def create_placeholder(*args):
    host = registered_host()
    builder = FusionTemplateBuilder(host)
    window = WorkfileBuildPlaceholderDialog(host, builder)
    window.exec_()


def update_placeholder(*args):
    host = registered_host()
    builder = FusionTemplateBuilder(host)
    placeholder_items_by_id = {
        placeholder_item.scene_identifier: placeholder_item
        for placeholder_item in builder.get_placeholders()
    }
    placeholder_items = []
    comp = get_current_comp()
    for node in comp.GetToolList(True, "Fuse.OPEmpty").values():
        node_name = node.Name
        if node_name in placeholder_items_by_id:
            placeholder_items.append(placeholder_items_by_id[node_name])

    # TODO show UI at least
    if len(placeholder_items) == 0:
        raise ValueError("No placeholder node selected")

    if len(placeholder_items) > 1:
        raise ValueError("Too many placeholder nodes selected")

    placeholder_item = placeholder_items[0]
    window = WorkfileBuildPlaceholderDialog(host, builder)
    window.set_update_mode(placeholder_item)
    window.exec_()
