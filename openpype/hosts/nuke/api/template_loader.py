import re
import collections

import nuke

from openpype.client import get_representations
from openpype.pipeline import legacy_io
from openpype.pipeline.workfile.abstract_template_loader import (
    AbstractPlaceholder,
    AbstractTemplateLoader,
)

from .lib import (
    find_free_space_to_paste_nodes,
    get_extreme_positions,
    get_group_io_nodes,
    imprint,
    refresh_node,
    refresh_nodes,
    reset_selection,
    get_names_from_nodes,
    get_nodes_by_names,
    select_nodes,
    duplicate_node,
    node_tempfile,
)

from .lib_template_builder import (
    delete_placeholder_attributes,
    get_placeholder_attributes,
    hide_placeholder_attributes
)

PLACEHOLDER_SET = "PLACEHOLDERS_SET"


class NukeTemplateLoader(AbstractTemplateLoader):
    """Concrete implementation of AbstractTemplateLoader for Nuke

    """

    def import_template(self, path):
        """Import template into current scene.
        Block if a template is already loaded.

        Args:
            path (str): A path to current template (usually given by
            get_template_path implementation)

        Returns:
            bool: Wether the template was succesfully imported or not
        """

        # TODO check if the template is already imported

        nuke.nodePaste(path)
        reset_selection()

        return True

    def preload(self, placeholder, loaders_by_name, last_representation):
        placeholder.data["nodes_init"] = nuke.allNodes()
        placeholder.data["last_repre_id"] = str(last_representation["_id"])

    def populate_template(self, ignored_ids=None):
        processed_key = "_node_processed"

        processed_nodes = []
        nodes = self.get_template_nodes()
        while nodes:
            # Mark nodes as processed so they're not re-executed
            # - that can happen if processing of placeholder node fails
            for node in nodes:
                imprint(node, {processed_key: True})
                processed_nodes.append(node)

            super(NukeTemplateLoader, self).populate_template(ignored_ids)

            # Recollect nodes to repopulate
            nodes = []
            for node in self.get_template_nodes():
                # Skip already processed nodes
                if (
                    processed_key in node.knobs()
                    and node.knob(processed_key).value()
                ):
                    continue
                nodes.append(node)

        for node in processed_nodes:
            if processed_key in node.knobs():
                nuke.removeKnob(node, processed_key)

    @staticmethod
    def get_template_nodes():
        placeholders = []
        all_groups = collections.deque()
        all_groups.append(nuke.thisGroup())
        while all_groups:
            group = all_groups.popleft()
            for node in group.nodes():
                if isinstance(node, nuke.Group):
                    all_groups.append(node)

                node_knobs = node.knobs()
                if (
                    "builder_type" not in node_knobs
                    or "is_placeholder" not in node_knobs
                    or not node.knob("is_placeholder").value()
                ):
                    continue

                if "empty" in node_knobs and node.knob("empty").value():
                    continue

                placeholders.append(node)

        return placeholders

    def update_missing_containers(self):
        nodes_by_id = collections.defaultdict(list)

        for node in nuke.allNodes():
            node_knobs = node.knobs().keys()
            if "repre_id" in node_knobs:
                repre_id = node.knob("repre_id").getValue()
                nodes_by_id[repre_id].append(node.name())

            if "empty" in node_knobs:
                node.removeKnob(node.knob("empty"))
                imprint(node, {"empty": False})

        for node_names in nodes_by_id.values():
            node = None
            for node_name in node_names:
                node_by_name = nuke.toNode(node_name)
                if "builder_type" in node_by_name.knobs().keys():
                    node = node_by_name
                    break

            if node is None:
                continue

            placeholder = nuke.nodes.NoOp()
            placeholder.setName("PLACEHOLDER")
            placeholder.knob("tile_color").setValue(4278190335)
            attributes = get_placeholder_attributes(node, enumerate=True)
            imprint(placeholder, attributes)
            pos_x = int(node.knob("x").getValue())
            pos_y = int(node.knob("y").getValue())
            placeholder.setXYpos(pos_x, pos_y)
            imprint(placeholder, {"nb_children": 1})
            refresh_node(placeholder)

        self.populate_template(self.get_loaded_containers_by_id())

    def get_loaded_containers_by_id(self):
        repre_ids = set()
        for node in nuke.allNodes():
            if "repre_id" in node.knobs():
                repre_ids.add(node.knob("repre_id").getValue())

        # Removes duplicates in the list
        return list(repre_ids)

    def delete_placeholder(self, placeholder):
        placeholder_node = placeholder.data["node"]
        last_loaded = placeholder.data["last_loaded"]
        if not placeholder.data["delete"]:
            if "empty" in placeholder_node.knobs().keys():
                placeholder_node.removeKnob(placeholder_node.knob("empty"))
            imprint(placeholder_node, {"empty": True})
            return

        if not last_loaded:
            nuke.delete(placeholder_node)
            return

        if "last_loaded" in placeholder_node.knobs().keys():
            for node_name in placeholder_node.knob("last_loaded").values():
                node = nuke.toNode(node_name)
                try:
                    delete_placeholder_attributes(node)
                except Exception:
                    pass

        last_loaded_names = [
            loaded_node.name()
            for loaded_node in last_loaded
        ]
        imprint(placeholder_node, {"last_loaded": last_loaded_names})

        for node in last_loaded:
            refresh_node(node)
            refresh_node(placeholder_node)
            if "builder_type" not in node.knobs().keys():
                attributes = get_placeholder_attributes(placeholder_node, True)
                imprint(node, attributes)
                imprint(node, {"is_placeholder": False})
                hide_placeholder_attributes(node)
                node.knob("is_placeholder").setVisible(False)
                imprint(
                    node,
                    {
                        "x": placeholder_node.xpos(),
                        "y": placeholder_node.ypos()
                    }
                )
                node.knob("x").setVisible(False)
                node.knob("y").setVisible(False)
        nuke.delete(placeholder_node)


class NukePlaceholder(AbstractPlaceholder):
    """Concrete implementation of AbstractPlaceholder for Nuke"""

    optional_keys = {"asset", "subset", "hierarchy"}

    def get_data(self, node):
        user_data = dict()
        node_knobs = node.knobs()
        for attr in self.required_keys.union(self.optional_keys):
            if attr in node_knobs:
                user_data[attr] = node_knobs[attr].getValue()
        user_data["node"] = node

        nb_children = 0
        if "nb_children" in node_knobs:
            nb_children = int(node_knobs["nb_children"].getValue())
        user_data["nb_children"] = nb_children

        siblings = []
        if "siblings" in node_knobs:
            siblings = node_knobs["siblings"].values()
        user_data["siblings"] = siblings

        node_full_name = node.fullName()
        user_data["group_name"] = node_full_name.rpartition(".")[0]
        user_data["last_loaded"] = []
        user_data["delete"] = False
        self.data = user_data

    def parent_in_hierarchy(self, containers):
        return

    def create_sib_copies(self):
        """ creating copies of the palce_holder siblings (the ones who were
        loaded with it) for the new nodes added

        Returns :
            copies (dict) : with copied nodes names and their copies
        """

        copies = {}
        siblings = get_nodes_by_names(self.data["siblings"])
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

    def fix_z_order(self):
        """Fix the problem of z_order when a backdrop is loaded."""

        nodes_loaded = self.data["last_loaded"]
        loaded_backdrops = []
        bd_orders = set()
        for node in nodes_loaded:
            if isinstance(node, nuke.BackdropNode):
                loaded_backdrops.append(node)
                bd_orders.add(node.knob("z_order").getValue())

        if not bd_orders:
            return

        sib_orders = set()
        for node_name in self.data["siblings"]:
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
                z_order + max_order - min_order + 1)

    def update_nodes(self, nodes, considered_nodes, offset_y=None):
        """Adjust backdrop nodes dimensions and positions.

        Considering some nodes sizes.

        Args:
            nodes (list): list of nodes to update
            considered_nodes (list): list of nodes to consider while updating
                positions and dimensions
            offset (int): distance between copies
        """

        placeholder_node = self.data["node"]

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
            siblings = get_nodes_by_names(self.data["siblings"])
            minX, _, maxX, _ = get_extreme_positions(siblings)
            diff_y = max_y - min_y + 20
            diff_x = abs(max_x - min_x - maxX + minX)
            contained_nodes = considered_nodes

        if diff_y <= 0 and diff_x <= 0:
            return

        for node in nodes:
            refresh_node(node)

            if (
                node == placeholder_node
                or node in considered_nodes
            ):
                continue

            if (
                not isinstance(node, nuke.BackdropNode)
                or (
                    isinstance(node, nuke.BackdropNode)
                    and not set(contained_nodes) <= set(node.getNodes())
                )
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

    def imprint_inits(self):
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

    def imprint_siblings(self):
        """
        - add siblings names to placeholder attributes (nodes loaded with it)
        - add Id to the attributes of all the other nodes
        """

        loaded_nodes = self.data["last_loaded"]
        loaded_nodes_set = set(loaded_nodes)
        data = {"repre_id": str(self.data["last_repre_id"])}

        for node in loaded_nodes:
            node_knobs = node.knobs()
            if "builder_type" not in node_knobs:
                # save the id of representation for all imported nodes
                imprint(node, data)
                node.knob("repre_id").setVisible(False)
                refresh_node(node)
                continue

            if (
                "is_placeholder" not in node_knobs
                or (
                    "is_placeholder" in node_knobs
                    and node.knob("is_placeholder").value()
                )
            ):
                siblings = list(loaded_nodes_set - {node})
                siblings_name = get_names_from_nodes(siblings)
                siblings = {"siblings": siblings_name}
                imprint(node, siblings)

    def set_loaded_connections(self):
        """
        set inputs and outputs of loaded nodes"""

        placeholder_node = self.data["node"]
        input_node, output_node = get_group_io_nodes(self.data["last_loaded"])
        for node in placeholder_node.dependent():
            for idx in range(node.inputs()):
                if node.input(idx) == placeholder_node:
                    node.setInput(idx, output_node)

        for node in placeholder_node.dependencies():
            for idx in range(placeholder_node.inputs()):
                if placeholder_node.input(idx) == node:
                    input_node.setInput(0, node)

    def set_copies_connections(self, copies):
        """Set inputs and outputs of the copies.

        Args:
            copies (dict): Copied nodes by their names.
        """

        last_input, last_output = get_group_io_nodes(self.data["last_loaded"])
        siblings = get_nodes_by_names(self.data["siblings"])
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

    def move_to_placeholder_group(self, nodes_loaded):
        """
        opening the placeholder's group and copying loaded nodes in it.

        Returns :
            nodes_loaded (list): the new list of pasted nodes
        """

        groups_name = self.data["group_name"]
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

    def clean(self):
        # deselect all selected nodes
        placeholder_node = self.data["node"]

        # getting the latest nodes added
        nodes_init = self.data["nodes_init"]
        nodes_loaded = list(set(nuke.allNodes()) - set(nodes_init))
        self.log.debug("Loaded nodes: {}".format(nodes_loaded))
        if not nodes_loaded:
            return

        self.data["delete"] = True

        nodes_loaded = self.move_to_placeholder_group(nodes_loaded)
        self.data["last_loaded"] = nodes_loaded
        refresh_nodes(nodes_loaded)

        # positioning of the loaded nodes
        min_x, min_y, _, _ = get_extreme_positions(nodes_loaded)
        for node in nodes_loaded:
            xpos = (node.xpos() - min_x) + placeholder_node.xpos()
            ypos = (node.ypos() - min_y) + placeholder_node.ypos()
            node.setXYpos(xpos, ypos)
        refresh_nodes(nodes_loaded)

        self.fix_z_order()  # fix the problem of z_order for backdrops
        self.imprint_siblings()

        if self.data["nb_children"] == 0:
            # save initial nodes postions and dimensions, update them
            # and set inputs and outputs of loaded nodes

            self.imprint_inits()
            self.update_nodes(nuke.allNodes(), nodes_loaded)
            self.set_loaded_connections()

        elif self.data["siblings"]:
            # create copies of placeholder siblings for the new loaded nodes,
            # set their inputs and outpus and update all nodes positions and
            # dimensions and siblings names

            siblings = get_nodes_by_names(self.data["siblings"])
            refresh_nodes(siblings)
            copies = self.create_sib_copies()
            new_nodes = list(copies.values())  # copies nodes
            self.update_nodes(new_nodes, nodes_loaded)
            placeholder_node.removeKnob(placeholder_node.knob("siblings"))
            new_nodes_name = get_names_from_nodes(new_nodes)
            imprint(placeholder_node, {"siblings": new_nodes_name})
            self.set_copies_connections(copies)

            self.update_nodes(
                nuke.allNodes(),
                new_nodes + nodes_loaded,
                20
            )

            new_siblings = get_names_from_nodes(new_nodes)
            self.data["siblings"] = new_siblings

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

        self.data["nb_children"] += 1
        reset_selection()
        # go back to root group
        nuke.root().begin()

    def get_representations(self, current_asset_doc, linked_asset_docs):
        project_name = legacy_io.active_project()

        builder_type = self.data["builder_type"]
        if builder_type == "context_asset":
            context_filters = {
                "asset": [re.compile(self.data["asset"])],
                "subset": [re.compile(self.data["subset"])],
                "hierarchy": [re.compile(self.data["hierarchy"])],
                "representations": [self.data["representation"]],
                "family": [self.data["family"]]
            }

        elif builder_type != "linked_asset":
            context_filters = {
                "asset": [
                    current_asset_doc["name"],
                    re.compile(self.data["asset"])
                ],
                "subset": [re.compile(self.data["subset"])],
                "hierarchy": [re.compile(self.data["hierarchy"])],
                "representation": [self.data["representation"]],
                "family": [self.data["family"]]
            }

        else:
            asset_regex = re.compile(self.data["asset"])
            linked_asset_names = []
            for asset_doc in linked_asset_docs:
                asset_name = asset_doc["name"]
                if asset_regex.match(asset_name):
                    linked_asset_names.append(asset_name)

            if not linked_asset_names:
                return []

            context_filters = {
                "asset": linked_asset_names,
                "subset": [re.compile(self.data["subset"])],
                "hierarchy": [re.compile(self.data["hierarchy"])],
                "representation": [self.data["representation"]],
                "family": [self.data["family"]],
            }

        return list(get_representations(
            project_name,
            context_filters=context_filters
        ))

    def err_message(self):
        return (
            "Error while trying to load a representation.\n"
            "Either the subset wasn't published or the template is malformed."
            "\n\n"
            "Builder was looking for:\n{attributes}".format(
                attributes="\n".join([
                    "{}: {}".format(key.title(), value)
                    for key, value in self.data.items()]
                )
            )
        )
