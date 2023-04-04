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
    comp_lock_and_undo_chunk,
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

        # placeholder_data = node.GetData("placeholder_data")
        # placeholder_data.update(new_placeholder_data)
        # node.SetData("placeholder_data", placeholder_data)

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
        for node in comp.GetToolList(False, "Fuse.OPEmpty").values():
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
        self.populate_load_placeholder(placeholder)

    def repopulate_placeholder(self, placeholder):
        repre_ids = self._get_loaded_repre_ids()
        self.populate_load_placeholder(placeholder, repre_ids)

    def get_placeholder_options(self, options=None):
        return self.get_load_plugin_options(options)

    def cleanup_placeholder(self, placeholder, failed):
        # deselect all selected nodes
        comp = get_current_comp()
        placeholder_node = comp.FindTool(placeholder.scene_identifier)

        # getting the latest nodes added
        # TODO get from shared populate data!
        nodes_init = placeholder.data["nodes_init"]
        added_nodes = []
        for node in comp.GetToolList().values():
            added_nodes.append(node.Name)
        nodes_loaded_names = list(set(added_nodes) - set(nodes_init))
        nodes_loaded = []
        for name in nodes_loaded_names:
            nodes_loaded.append(comp.FindTool(name))

        self.log.debug("Loaded nodes: {}".format(nodes_loaded))

        if not nodes_loaded:
            return

        placeholder.data["delete"] = True

        nodes_loaded = self._move_to_placeholder_group(
            placeholder, nodes_loaded
        )
        placeholder.data["last_loaded"] = nodes_loaded

        # positioning of the loaded nodes
        # FUSION! - I don't think this is needed at all?

        # flow = comp.CurrentFrame.FlowView
        # min_x, min_y, _, _ = get_extreme_positions(nodes_loaded)
        # for node in nodes_loaded:
        #    node_xPos, node_yPos = flow.GetPosTable(node).values()
        #    placeholder_xPos, placeholder_yPos = flow.GetPosTable(
        #        placeholder_node
        #    ).values()
        #    xpos = (node_xPos - min_x) + placeholder_xPos
        #    ypos = (node_yPos - min_y) + placeholder_yPos
        #    flow.SetPos(node, xpos, ypos)

        # fix the problem of z_order for backdrops
        self._setdata_siblings(placeholder)
        self._imprint_siblings(placeholder)

        if placeholder.data["nb_children"] == 0:
            # save initial nodes postions and dimensions, update them
            # and set inputs and outputs of loaded nodes

            self._imprint_inits()
            self._update_nodes(placeholder, nuke.allNodes(), nodes_loaded)
            self._set_loaded_connections(placeholder)

        elif placeholder.data["siblings"]:
            # create copies of placeholder siblings for the new loaded nodes,
            # set their inputs and outpus and update all nodes positions and
            # dimensions and siblings names

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

        else:
            # if the placeholder doesn't have siblings, the loaded
            # nodes will be placed in a free space

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

        placeholder.data["nb_children"] += 1
        reset_selection()

        # remove placeholders marked as delete
        if placeholder.data.get("delete") and not placeholder.data.get(
            "keep_placeholder"
        ):
            self.log.debug(
                "Deleting node: {}".format(placeholder_node.name())
            )
            nuke.delete(placeholder_node)

        # go back to root group
        nuke.root().begin()

    def _move_to_placeholder_group(self, placeholder, nodes_loaded):
        """
        opening the placeholder's group and copying loaded nodes in it.

        Returns :
            nodes_loaded (list): the new list of pasted nodes
        """

        groups_name = placeholder.data["group_name"]
        reset_selection()
        select_nodes(nodes_loaded)
        if groups_name:
            with node_tempfile() as filepath:
                nuke.nodeCopy(filepath)
                for node in nuke.selectedNodes():
                    nuke.delete(node)
                group = nuke.toNode(groups_name)
                group.begin()
                nuke.nodePaste(filepath)
                nodes_loaded = nuke.selectedNodes()
        return nodes_loaded

    def _fix_z_order(self, placeholder):
        """Fix the problem of z_order when a backdrop is loaded."""

        nodes_loaded = placeholder.data["last_loaded"]
        loaded_backdrops = []
        bd_orders = set()
        for node in nodes_loaded:
            if isinstance(node, nuke.BackdropNode):
                loaded_backdrops.append(node)
                bd_orders.add(node.knob("z_order").getValue())

        if not bd_orders:
            return

        sib_orders = set()
        for node_name in placeholder.data["siblings"]:
            node = nuke.toNode(node_name)
            if isinstance(node, nuke.BackdropNode):
                sib_orders.add(node.knob("z_order").getValue())

        if not sib_orders:
            return

        min_order = min(bd_orders)
        max_order = max(sib_orders)
        for backdrop_node in loaded_backdrops:
            z_order = backdrop_node.knob("z_order").getValue()
            backdrop_node.knob("z_order").setValue(
                z_order + max_order - min_order + 1
            )

    def _imprint_siblings(self, placeholder):
        """
        - add siblings names to placeholder attributes (nodes loaded with it)
        - add Id to the attributes of all the other nodes
        """

        loaded_nodes = placeholder.data["last_loaded"]
        loaded_nodes_set = set(loaded_nodes)
        data = {"repre_id": str(placeholder.data["last_repre_id"])}

        for node in loaded_nodes:
            node_knobs = node.knobs()
            if "builder_type" not in node_knobs:
                # save the id of representation for all imported nodes
                imprint(node, data)
                node.knob("repre_id").setVisible(False)
                refresh_node(node)
                continue

            if "is_placeholder" not in node_knobs or (
                "is_placeholder" in node_knobs
                and node.knob("is_placeholder").value()
            ):
                siblings = list(loaded_nodes_set - {node})
                siblings_name = get_names_from_nodes(siblings)
                siblings = {"siblings": siblings_name}
                imprint(node, siblings)

    def _imprint_inits(self):
        """Add initial positions and dimensions to the attributes"""

        for node in nuke.allNodes():
            refresh_node(node)
            imprint(node, {"x_init": node.xpos(), "y_init": node.ypos()})
            node.knob("x_init").setVisible(False)
            node.knob("y_init").setVisible(False)
            width = node.screenWidth()
            height = node.screenHeight()
            if "bdwidth" in node.knobs():
                imprint(node, {"w_init": width, "h_init": height})
                node.knob("w_init").setVisible(False)
                node.knob("h_init").setVisible(False)
            refresh_node(node)

    def _update_nodes(
        self, placeholder, nodes, considered_nodes, offset_y=None
    ):
        """Adjust backdrop nodes dimensions and positions.

        Considering some nodes sizes.

        Args:
            nodes (list): list of nodes to update
            considered_nodes (list): list of nodes to consider while updating
                positions and dimensions
            offset (int): distance between copies
        """

        placeholder_node = nuke.toNode(placeholder.scene_identifier)

        min_x, min_y, max_x, max_y = get_extreme_positions(considered_nodes)

        diff_x = diff_y = 0
        contained_nodes = []  # for backdrops

        if offset_y is None:
            width_ph = placeholder_node.screenWidth()
            height_ph = placeholder_node.screenHeight()
            diff_y = max_y - min_y - height_ph
            diff_x = max_x - min_x - width_ph
            contained_nodes = [placeholder_node]
            min_x = placeholder_node.xpos()
            min_y = placeholder_node.ypos()
        else:
            siblings = get_nodes_by_names(placeholder.data["siblings"])
            minX, _, maxX, _ = get_extreme_positions(siblings)
            diff_y = max_y - min_y + 20
            diff_x = abs(max_x - min_x - maxX + minX)
            contained_nodes = considered_nodes

        if diff_y <= 0 and diff_x <= 0:
            return

        for node in nodes:
            refresh_node(node)

            if node == placeholder_node or node in considered_nodes:
                continue

            if not isinstance(node, nuke.BackdropNode) or (
                isinstance(node, nuke.BackdropNode)
                and not set(contained_nodes) <= set(node.getNodes())
            ):
                if offset_y is None and node.xpos() >= min_x:
                    node.setXpos(node.xpos() + diff_x)

                if node.ypos() >= min_y:
                    node.setYpos(node.ypos() + diff_y)

            else:
                width = node.screenWidth()
                height = node.screenHeight()
                node.knob("bdwidth").setValue(width + diff_x)
                node.knob("bdheight").setValue(height + diff_y)

            refresh_node(node)

    def _set_loaded_connections(self, placeholder):
        """
        set inputs and outputs of loaded nodes"""

        placeholder_node = nuke.toNode(placeholder.scene_identifier)
        input_node, output_node = get_group_io_nodes(
            placeholder.data["last_loaded"]
        )
        for node in placeholder_node.dependent():
            for idx in range(node.inputs()):
                if node.input(idx) == placeholder_node and output_node:
                    node.setInput(idx, output_node)

        for node in placeholder_node.dependencies():
            for idx in range(placeholder_node.inputs()):
                if placeholder_node.input(idx) == node and input_node:
                    input_node.setInput(0, node)

    def _create_sib_copies(self, placeholder):
        """creating copies of the palce_holder siblings (the ones who were
        loaded with it) for the new nodes added

        Returns :
            copies (dict) : with copied nodes names and their copies
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

    def _set_copies_connections(self, placeholder, copies):
        """Set inputs and outputs of the copies.

        Args:
            copies (dict): Copied nodes by their names.
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


class FusionPlaceholderCreatePlugin(
    FusionPlaceholderPlugin, PlaceholderCreateMixin
):
    identifier = "fusion.create"
    label = "Fusion create"

    def _parse_placeholder_node_data(self, node):
        placeholder_data = super(
            FusionPlaceholderCreatePlugin, self
        )._parse_placeholder_node_data(node)

        node_knobs = node.knobs()
        nb_children = 0
        if "nb_children" in node_knobs:
            nb_children = int(node_knobs["nb_children"].getValue())
        placeholder_data["nb_children"] = nb_children

        siblings = []
        if "siblings" in node_knobs:
            siblings = node_knobs["siblings"].values()
        placeholder_data["siblings"] = siblings

        node_full_name = node.fullName()
        placeholder_data["group_name"] = node_full_name.rpartition(".")[0]
        placeholder_data["last_loaded"] = []
        placeholder_data["delete"] = False
        return placeholder_data

    def _before_instance_create(self, placeholder):
        placeholder.data["nodes_init"] = nuke.allNodes()

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
        self.populate_create_placeholder(placeholder)

    def repopulate_placeholder(self, placeholder):
        self.populate_create_placeholder(placeholder)

    def get_placeholder_options(self, options=None):
        return self.get_create_plugin_options(options)

    def cleanup_placeholder(self, placeholder, failed):
        # deselect all selected nodes
        placeholder_node = nuke.toNode(placeholder.scene_identifier)

        # getting the latest nodes added
        nodes_init = placeholder.data["nodes_init"]
        nodes_created = list(set(nuke.allNodes()) - set(nodes_init))
        self.log.debug("Created nodes: {}".format(nodes_created))
        if not nodes_created:
            return

        placeholder.data["delete"] = True

        nodes_created = self._move_to_placeholder_group(
            placeholder, nodes_created
        )
        placeholder.data["last_created"] = nodes_created
        refresh_nodes(nodes_created)

        # positioning of the created nodes
        min_x, min_y, _, _ = get_extreme_positions(nodes_created)
        for node in nodes_created:
            xpos = (node.xpos() - min_x) + placeholder_node.xpos()
            ypos = (node.ypos() - min_y) + placeholder_node.ypos()
            node.setXYpos(xpos, ypos)
        refresh_nodes(nodes_created)

        # fix the problem of z_order for backdrops
        self._fix_z_order(placeholder)
        self._imprint_siblings(placeholder)

        if placeholder.data["nb_children"] == 0:
            # save initial nodes postions and dimensions, update them
            # and set inputs and outputs of created nodes

            self._imprint_inits()
            self._update_nodes(placeholder, nuke.allNodes(), nodes_created)
            self._set_created_connections(placeholder)

        elif placeholder.data["siblings"]:
            # create copies of placeholder siblings for the new created nodes,
            # set their inputs and outpus and update all nodes positions and
            # dimensions and siblings names

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

        else:
            # if the placeholder doesn't have siblings, the created
            # nodes will be placed in a free space

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

        placeholder.data["nb_children"] += 1
        reset_selection()

        # remove placeholders marked as delete
        if placeholder.data.get("delete") and not placeholder.data.get(
            "keep_placeholder"
        ):
            self.log.debug(
                "Deleting node: {}".format(placeholder_node.name())
            )
            nuke.delete(placeholder_node)

        # go back to root group
        nuke.root().begin()

    def _move_to_placeholder_group(self, placeholder, nodes_created):
        """
        opening the placeholder's group and copying created nodes in it.

        Returns :
            nodes_created (list): the new list of pasted nodes
        """
        groups_name = placeholder.data["group_name"]
        reset_selection()
        select_nodes(nodes_created)
        if groups_name:
            with node_tempfile() as filepath:
                nuke.nodeCopy(filepath)
                for node in nuke.selectedNodes():
                    nuke.delete(node)
                group = nuke.toNode(groups_name)
                group.begin()
                nuke.nodePaste(filepath)
                nodes_created = nuke.selectedNodes()
        return nodes_created

    def _fix_z_order(self, placeholder):
        """Fix the problem of z_order when a backdrop is create."""

        nodes_created = placeholder.data["last_created"]
        created_backdrops = []
        bd_orders = set()
        for node in nodes_created:
            if isinstance(node, nuke.BackdropNode):
                created_backdrops.append(node)
                bd_orders.add(node.knob("z_order").getValue())

        if not bd_orders:
            return

        sib_orders = set()
        for node_name in placeholder.data["siblings"]:
            node = nuke.toNode(node_name)
            if isinstance(node, nuke.BackdropNode):
                sib_orders.add(node.knob("z_order").getValue())

        if not sib_orders:
            return

        min_order = min(bd_orders)
        max_order = max(sib_orders)
        for backdrop_node in created_backdrops:
            z_order = backdrop_node.knob("z_order").getValue()
            backdrop_node.knob("z_order").setValue(
                z_order + max_order - min_order + 1
            )

    def _imprint_siblings(self, placeholder):
        """
        - add siblings names to placeholder attributes (nodes created with it)
        - add Id to the attributes of all the other nodes
        """

        created_nodes = placeholder.data["last_created"]
        created_nodes_set = set(created_nodes)

        for node in created_nodes:
            node_knobs = node.knobs()

            if "is_placeholder" not in node_knobs or (
                "is_placeholder" in node_knobs
                and node.knob("is_placeholder").value()
            ):
                siblings = list(created_nodes_set - {node})
                siblings_name = get_names_from_nodes(siblings)
                siblings = {"siblings": siblings_name}
                imprint(node, siblings)

    def _imprint_inits(self):
        """Add initial positions and dimensions to the attributes"""

        for node in nuke.allNodes():
            refresh_node(node)
            imprint(node, {"x_init": node.xpos(), "y_init": node.ypos()})
            node.knob("x_init").setVisible(False)
            node.knob("y_init").setVisible(False)
            width = node.screenWidth()
            height = node.screenHeight()
            if "bdwidth" in node.knobs():
                imprint(node, {"w_init": width, "h_init": height})
                node.knob("w_init").setVisible(False)
                node.knob("h_init").setVisible(False)
            refresh_node(node)

    def _update_nodes(
        self, placeholder, nodes, considered_nodes, offset_y=None
    ):
        """Adjust backdrop nodes dimensions and positions.

        Considering some nodes sizes.

        Args:
            nodes (list): list of nodes to update
            considered_nodes (list): list of nodes to consider while updating
                positions and dimensions
            offset (int): distance between copies
        """

        placeholder_node = nuke.toNode(placeholder.scene_identifier)

        min_x, min_y, max_x, max_y = get_extreme_positions(considered_nodes)

        diff_x = diff_y = 0
        contained_nodes = []  # for backdrops

        if offset_y is None:
            width_ph = placeholder_node.screenWidth()
            height_ph = placeholder_node.screenHeight()
            diff_y = max_y - min_y - height_ph
            diff_x = max_x - min_x - width_ph
            contained_nodes = [placeholder_node]
            min_x = placeholder_node.xpos()
            min_y = placeholder_node.ypos()
        else:
            siblings = get_nodes_by_names(placeholder.data["siblings"])
            minX, _, maxX, _ = get_extreme_positions(siblings)
            diff_y = max_y - min_y + 20
            diff_x = abs(max_x - min_x - maxX + minX)
            contained_nodes = considered_nodes

        if diff_y <= 0 and diff_x <= 0:
            return

        for node in nodes:
            refresh_node(node)

            if node == placeholder_node or node in considered_nodes:
                continue

            if not isinstance(node, nuke.BackdropNode) or (
                isinstance(node, nuke.BackdropNode)
                and not set(contained_nodes) <= set(node.getNodes())
            ):
                if offset_y is None and node.xpos() >= min_x:
                    node.setXpos(node.xpos() + diff_x)

                if node.ypos() >= min_y:
                    node.setYpos(node.ypos() + diff_y)

            else:
                width = node.screenWidth()
                height = node.screenHeight()
                node.knob("bdwidth").setValue(width + diff_x)
                node.knob("bdheight").setValue(height + diff_y)

            refresh_node(node)

    def _set_created_connections(self, placeholder):
        """
        set inputs and outputs of created nodes"""

        placeholder_node = nuke.toNode(placeholder.scene_identifier)
        input_node, output_node = get_group_io_nodes(
            placeholder.data["last_created"]
        )
        for node in placeholder_node.dependent():
            for idx in range(node.inputs()):
                if node.input(idx) == placeholder_node and output_node:
                    node.setInput(idx, output_node)

        for node in placeholder_node.dependencies():
            for idx in range(placeholder_node.inputs()):
                if placeholder_node.input(idx) == node and input_node:
                    input_node.setInput(0, node)

    def _create_sib_copies(self, placeholder):
        """creating copies of the palce_holder siblings (the ones who were
        created with it) for the new nodes added

        Returns :
            copies (dict) : with copied nodes names and their copies
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

    def _set_copies_connections(self, placeholder, copies):
        """Set inputs and outputs of the copies.

        Args:
            copies (dict): Copied nodes by their names.
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
