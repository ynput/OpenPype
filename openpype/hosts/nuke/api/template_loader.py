from openpype.hosts.nuke.api.lib_template_builder import (
    delete_placeholder_attributes, get_placeholder_attributes,
    hide_placeholder_attributes)
from openpype.lib.abstract_template_loader import (
    AbstractPlaceholder,
    AbstractTemplateLoader)
import nuke
from collections import defaultdict
from openpype.hosts.nuke.api.lib import (
    find_free_space_to_paste_nodes, get_extremes, get_io, imprint,
    refresh_node, refresh_nodes, reset_selection,
    get_names_from_nodes, get_nodes_from_names, select_nodes)
PLACEHOLDER_SET = 'PLACEHOLDERS_SET'


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
        placeholder.data["_id"] = last_representation['_id']

    def populate_template(self, ignored_ids=None):
        place_holders = self.get_template_nodes()
        while len(place_holders) > 0:
            super().populate_template(ignored_ids)
            place_holders = self.get_template_nodes()

    @staticmethod
    def get_template_nodes():
        placeholders = []
        allGroups = [nuke.thisGroup()]
        while len(allGroups) > 0:
            group = allGroups.pop(0)
            for node in group.nodes():
                if "builder_type" in node.knobs().keys() and (
                    'is_placeholder' not in node.knobs().keys()
                        or 'is_placeholder' in node.knobs().keys()
                        and node.knob('is_placeholder').value()):
                    if 'empty' in node.knobs().keys()\
                            and node.knob('empty').value():
                        continue
                    placeholders += [node]
                if isinstance(node, nuke.Group):
                    allGroups.append(node)

        return placeholders

    def update_missing_containers(self):
        nodes_byId = {}
        nodes_byId = defaultdict(lambda: [], nodes_byId)

        for n in nuke.allNodes():
            if 'id_rep' in n.knobs().keys():
                nodes_byId[n.knob('id_rep').getValue()] += [n.name()]
        for s in nodes_byId.values():
            n = None
            for name in s:
                n = nuke.toNode(name)
                if 'builder_type' in n.knobs().keys():
                    break
            if n is not None and 'builder_type' in n.knobs().keys():

                placeholder = nuke.nodes.NoOp()
                placeholder.setName('PLACEHOLDER')
                placeholder.knob('tile_color').setValue(4278190335)
                attributes = get_placeholder_attributes(n, enumerate=True)
                imprint(placeholder, attributes)
                x = int(n.knob('x').getValue())
                y = int(n.knob('y').getValue())
                placeholder.setXYpos(x, y)
                imprint(placeholder, {'nb_children': 1})
                refresh_node(placeholder)

        self.populate_template(self.get_loaded_containers_by_id())

    def get_loaded_containers_by_id(self):
        ids = []
        for n in nuke.allNodes():
            if 'id_rep' in n.knobs():
                ids.append(n.knob('id_rep').getValue())

        # Removes duplicates in the list
        ids = list(set(ids))
        return ids

    def get_placeholders(self):
        placeholders = super().get_placeholders()
        return placeholders

    def delete_placeholder(self, placeholder):
        node = placeholder.data['node']
        lastLoaded = placeholder.data['last_loaded']
        if 'delete' in placeholder.data.keys()\
                and placeholder.data['delete'] is False:
            imprint(node, {"empty": True})
        else:
            if lastLoaded:
                if 'last_loaded' in node.knobs().keys():
                    for s in node.knob('last_loaded').values():
                        n = nuke.toNode(s)
                        try:
                            delete_placeholder_attributes(n)
                        except Exception:
                            pass

                lastLoaded_names = []
                for loadedNode in lastLoaded:
                    lastLoaded_names.append(loadedNode.name())
                imprint(node, {'last_loaded': lastLoaded_names})

                for n in lastLoaded:
                    refresh_node(n)
                    refresh_node(node)
                    if 'builder_type' not in n.knobs().keys():
                        attributes = get_placeholder_attributes(node, True)
                        imprint(n, attributes)
                        imprint(n, {'is_placeholder': False})
                        hide_placeholder_attributes(n)
                        n.knob('is_placeholder').setVisible(False)
                        imprint(n, {'x': node.xpos(), 'y': node.ypos()})
                        n.knob('x').setVisible(False)
                        n.knob('y').setVisible(False)
            nuke.delete(node)


class NukePlaceholder(AbstractPlaceholder):
    """Concrete implementation of AbstractPlaceholder for Nuke

    """

    optional_attributes = {'asset', 'subset', 'hierarchy'}

    def get_data(self, node):
        user_data = dict()
        dictKnobs = node.knobs()
        for attr in self.attributes.union(self.optional_attributes):
            if attr in dictKnobs.keys():
                user_data[attr] = dictKnobs[attr].getValue()
        user_data['node'] = node

        if 'nb_children' in dictKnobs.keys():
            user_data['nb_children'] = int(dictKnobs['nb_children'].getValue())
        else:
            user_data['nb_children'] = 0
        if 'siblings' in dictKnobs.keys():
            user_data['siblings'] = dictKnobs['siblings'].values()
        else:
            user_data['siblings'] = []

        fullName = node.fullName()
        user_data['group_name'] = fullName.rpartition('.')[0]
        user_data['last_loaded'] = []

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
        siblings = get_nodes_from_names(self.data['siblings'])
        for n in siblings:
            reset_selection()
            n.setSelected(True)
            nuke.nodeCopy("%clipboard%")
            reset_selection()
            nuke.nodePaste("%clipboard%")
            new_node = nuke.selectedNodes()[0]
            x_init = int(new_node.knob('x_init').getValue())
            y_init = int(new_node.knob('y_init').getValue())
            new_node.setXYpos(x_init, y_init)
            if isinstance(new_node, nuke.BackdropNode):
                w_init = new_node.knob('w_init').getValue()
                h_init = new_node.knob('h_init').getValue()
                new_node.knob('bdwidth').setValue(w_init)
                new_node.knob('bdheight').setValue(h_init)
                refresh_node(n)

            if 'id_rep' in n.knobs().keys():
                n.removeKnob(n.knob('id_rep'))
            copies[n.name()] = new_node
        return copies

    def fix_z_order(self):
        """
        fix the problem of z_order when a backdrop is loaded
        """
        orders_bd = []
        nodes_loaded = self.data['last_loaded']
        for n in nodes_loaded:
            if isinstance(n, nuke.BackdropNode):
                orders_bd.append(n.knob("z_order").getValue())

        if orders_bd:

            min_order = min(orders_bd)
            siblings = self.data["siblings"]

            orders_sib = []
            for s in siblings:
                n = nuke.toNode(s)
                if isinstance(n, nuke.BackdropNode):
                    orders_sib.append(n.knob("z_order").getValue())
            if orders_sib:
                max_order = max(orders_sib)
                for n in nodes_loaded:
                    if isinstance(n, nuke.BackdropNode):
                        z_order = n.knob("z_order").getValue()
                        n.knob("z_order").setValue(
                            z_order + max_order - min_order + 1)

    def update_nodes(self, nodes, considered_nodes, offset_y=None):
        """ Adjust backdrop nodes dimensions and positions considering some nodes
            sizes

        Arguments:
            nodes (list): list of nodes to update
            considered_nodes (list) : list of nodes to consider while updating
                                      positions and dimensions
            offset (int) : distance between copies
        """
        node = self.data['node']

        min_x, min_y, max_x, max_y = get_extremes(considered_nodes)

        diff_x = diff_y = 0
        contained_nodes = []  # for backdrops

        if offset_y is None:
            width_ph = node.screenWidth()
            height_ph = node.screenHeight()
            diff_y = max_y - min_y - height_ph
            diff_x = max_x - min_x - width_ph
            contained_nodes = [node]
            min_x = node.xpos()
            min_y = node.ypos()
        else:
            siblings = get_nodes_from_names(self.data['siblings'])
            minX, _, maxX, _ = get_extremes(siblings)
            diff_y = max_y - min_y + 20
            diff_x = abs(max_x - min_x - maxX + minX)
            contained_nodes = considered_nodes

        if diff_y > 0 or diff_x > 0:
            for n in nodes:
                refresh_node(n)
                if n != node and n not in considered_nodes:

                    if not isinstance(n, nuke.BackdropNode)\
                            or isinstance(n, nuke.BackdropNode)\
                            and not set(contained_nodes) <= set(n.getNodes()):
                        if offset_y is None and n.xpos() >= min_x:
                            n.setXpos(n.xpos() + diff_x)

                        if n.ypos() >= min_y:
                            n.setYpos(n.ypos() + diff_y)

                    else:
                        width = n.screenWidth()
                        height = n.screenHeight()
                        n.knob("bdwidth").setValue(width + diff_x)
                        n.knob("bdheight").setValue(height + diff_y)

                    refresh_node(n)

    def imprint_inits(self):
        """
        add initial positions and dimensions to the attributes
        """
        for n in nuke.allNodes():
            refresh_node(n)
            imprint(n, {'x_init': n.xpos(), 'y_init': n.ypos()})
            n.knob('x_init').setVisible(False)
            n.knob('y_init').setVisible(False)
            width = n.screenWidth()
            height = n.screenHeight()
            if 'bdwidth' in n.knobs().keys():
                imprint(n, {'w_init': width, 'h_init': height})
                n.knob('w_init').setVisible(False)
                n.knob('h_init').setVisible(False)

    def imprint_siblings(self):
        """
        - add siblings names to placeholder attributes (nodes loaded with it)
        - add Id to the attributes of all the other nodes
        """

        nodes_loaded = self.data['last_loaded']
        d = {"id_rep": str(self.data['_id'])}

        for n in nodes_loaded:
            if "builder_type" in n.knobs().keys()\
                    and ('is_placeholder' not in n.knobs().keys()
                         or 'is_placeholder' in n.knobs().keys()
                         and n.knob('is_placeholder').value()):

                siblings = list(set(nodes_loaded) - set([n]))
                siblings_name = get_names_from_nodes(siblings)
                siblings = {"siblings": siblings_name}
                imprint(n, siblings)

            elif 'builder_type' not in n.knobs().keys():
                # save the id of representation for all imported nodes
                imprint(n, d)
                n.knob('id_rep').setVisible(False)
                refresh_node(n)

    def set_loaded_connections(self):
        """
        set inputs and outputs of loaded nodes"""

        node = self.data['node']
        input, output = get_io(self.data['last_loaded'])
        for n in node.dependent():
            for i in range(n.inputs()):
                if n.input(i) == node:
                    n.setInput(i, output)

        for n in node.dependencies():
            for i in range(node.inputs()):
                if node.input(i) == n:
                    input.setInput(0, n)

    def set_copies_connections(self, copies):
        """
        set inputs and outputs of the copies

        Arguments :
            copies (dict) : with copied nodes names and their copies
        """
        input, output = get_io(self.data['last_loaded'])
        siblings = get_nodes_from_names(self.data['siblings'])
        inp, out = get_io(siblings)
        inp_copy, out_copy = (copies[inp.name()], copies[out.name()])

        for node_init in siblings:
            if node_init != out:
                node_copy = copies[node_init.name()]
                for n in node_init.dependent():
                    for i in range(n.inputs()):
                        if n.input(i) == node_init:
                            if n in siblings:
                                copies[n.name()].setInput(i, node_copy)
                            else:
                                input.setInput(0, node_copy)

                for n in node_init.dependencies():
                    for i in range(node_init.inputs()):
                        if node_init.input(i) == n:
                            if node_init == inp:
                                inp_copy.setInput(i, n)
                            elif n in siblings:
                                node_copy.setInput(i, copies[n.name()])
                            else:
                                node_copy.setInput(i, output)

        inp.setInput(0, out_copy)

    def move_to_placeholder_group(self, nodes_loaded):
        """
        opening the placeholder's group and copying loaded nodes in it"""
        groups_name = self.data['group_name']
        reset_selection()
        select_nodes(nodes_loaded)
        if groups_name:
            nuke.nodeCopy("%clipboard%")
            for n in nuke.selectedNodes():
                nuke.delete(n)
            group = nuke.toNode(groups_name)
            group.begin()
            nuke.nodePaste("%clipboard%")
            nodes_loaded = nuke.selectedNodes()
        return nodes_loaded

    def clean(self):

        # deselect all selected nodes
        node = self.data['node']

        # getting the latest nodes added
        nodes_init = self.data["nodes_init"]
        nodes_loaded = list(set(nuke.allNodes()) - set(nodes_init))
        if not nodes_loaded:
            self.data['delete'] = False
            return
        nodes_loaded = self.move_to_placeholder_group(nodes_loaded)
        self.data['last_loaded'] = nodes_loaded
        refresh_nodes(nodes_loaded)

        # positioning of the loaded nodes
        min_x, min_y, _, _ = get_extremes(nodes_loaded)
        for n in nodes_loaded:
            xpos = (n.xpos() - min_x) + node.xpos()
            ypos = (n.ypos() - min_y) + node.ypos()
            n.setXYpos(xpos, ypos)
        refresh_nodes(nodes_loaded)

        self.fix_z_order()  # fix the problem of z_order for backdrops
        self.imprint_siblings()

        if self.data['nb_children'] == 0:
            # save initial nodes postions and dimensions, update them
            # and set inputs and outputs of loaded nodes

            self.imprint_inits()
            self.update_nodes(nuke.allNodes(), nodes_loaded)
            self.set_loaded_connections()

        elif self.data['siblings']:
            # create copies of placeholder siblings for the new loaded nodes,
            # set their inputs and outpus and update all nodes positions and
            # dimensions and siblings names

            siblings = get_nodes_from_names(self.data['siblings'])
            refresh_nodes(siblings)
            copies = self.create_sib_copies()
            new_nodes = list(copies.values())  # copies nodes
            self.update_nodes(new_nodes, nodes_loaded)
            node.removeKnob(node.knob('siblings'))
            new_nodes_name = get_names_from_nodes(new_nodes)
            imprint(node, {'siblings': new_nodes_name})
            self.set_copies_connections(copies)

            self.update_nodes(nuke.allNodes(),
                              new_nodes + nodes_loaded, 20)

            new_siblings = get_names_from_nodes(new_nodes)
            self.data['siblings'] = new_siblings

        else:
            # if the placeholder doesn't have siblings, the loaded
            # nodes will be placed in a free space

            xpointer, ypointer = find_free_space_to_paste_nodes(
                nodes_loaded, direction="bottom", offset=200
            )
            n = nuke.createNode("NoOp")
            reset_selection()
            nuke.delete(n)
            for n in nodes_loaded:
                xpos = (n.xpos() - min_x) + xpointer
                ypos = (n.ypos() - min_y) + ypointer
                n.setXYpos(xpos, ypos)

        self.data['nb_children'] += 1
        reset_selection()
        # go back to root group
        nuke.root().begin()

    def convert_to_db_filters(self, current_asset, linked_asset):
        if self.data['builder_type'] == "context_asset":
            return [{
                "type": "representation",
                "context.asset": {
                    "$eq": current_asset, "$regex": self.data['asset']},
                "context.subset": {"$regex": self.data['subset']},
                "context.hierarchy": {"$regex": self.data['hierarchy']},
                "context.representation": self.data['representation'],
                "context.family": self.data['family'],
            }]

        elif self.data['builder_type'] == "linked_asset":
            return [{
                "type": "representation",
                "context.asset": {
                    "$eq": asset_name, "$regex": self.data['asset']},
                "context.subset": {"$regex": self.data['subset']},
                "context.hierarchy": {"$regex": self.data['hierarchy']},
                "context.representation": self.data['representation'],
                "context.family": self.data['family'],
            } for asset_name in linked_asset]

        else:
            return [{
                "type": "representation",
                "context.asset": {"$regex": self.data['asset']},
                "context.subset": {"$regex": self.data['subset']},
                "context.hierarchy": {"$regex": self.data['hierarchy']},
                "context.representation": self.data['representation'],
                "context.family": self.data['family'],
            }]

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
