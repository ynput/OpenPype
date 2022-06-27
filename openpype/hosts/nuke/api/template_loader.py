
from time import sleep
from openpype.hosts.nuke.api.lib_template_builder import delete_placeholder_attributes, get_placeholder_attributes, hide_placeholder_attributes, placeholder_window
from openpype.lib.abstract_template_loader import (
    AbstractPlaceholder,
    AbstractTemplateLoader)
from openpype.lib.build_template_exceptions import TemplateAlreadyImported
import nuke
from openpype.hosts.nuke.api.lib import (
    find_free_space_to_paste_nodes, get_extremes, get_io, imprint, refresh_node, reset_selection, select_nodes )
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
        
        #TODO check if the template is already imported

        nuke.nodePaste(path)
        reset_selection()
    

        return True

    def preload(self, placeholder, loaders_by_name, last_representation):
        placeholder.data["nodes_init"] = nuke.allNodes()
        placeholder.data["_id"] = last_representation['_id']




    def populate_template(self, ignored_ids=None) :
        place_holders = self.get_template_nodes()
        while len(place_holders) > 0 :
            super().populate_template(ignored_ids)
            place_holders = self.get_template_nodes()


    @staticmethod
    def get_template_nodes():
        attributes = []
        groups = [nuke.thisGroup()]
        while len(groups) > 0 :
            group = groups.pop(0)  

            for node in group.nodes() :
                if "builder_type" in node.knobs().keys() and  ( 'is_placeholder' not in  node.knobs().keys() or  'is_placeholder' in  node.knobs().keys() \
                    and node.knob('is_placeholder').value() ) :
                    attributes += [node]
                if isinstance(node,nuke.Group) : 
                    groups.append(node)
     
                
        return attributes

    def update_missing_containers(self):
        d = {}

        for n in nuke.allNodes():
            refresh_node(n)
            if 'id_rep' in n.knobs().keys():
                d[n.knob('id_rep').getValue()] = []
        for n in nuke.allNodes():
            if 'id_rep' in n.knobs().keys():
                d[n.knob('id_rep').getValue()] += [n.name()]
        for s in d.values() :
            for name in s :
                n = nuke.toNode(name)
                if 'builder_type' in n.knobs().keys():
                    break
            if 'builder_type' not in n.knobs().keys():
                continue

            print("je suis rentré")
            placeholder = nuke.nodes.NoOp()
            placeholder.setName('PLACEHOLDER')
            placeholder.knob('tile_color').setValue(4278190335)
            imprint(placeholder, get_placeholder_attributes(n, enumerate= True))
            print(n.name(), "anananan")
            placeholder.setXYpos(int(n.knob('x').getValue()), int(n.knob('y').getValue()))
            imprint(placeholder, {'nb_children' : 1})
            refresh_node(placeholder)

        self.populate_template(self.get_loaded_containers_by_id())

    def get_loaded_containers_by_id(self):
        ids = {}
        for n in nuke.allNodes():
            if 'id_rep' in n.knobs().keys():
                ids[n.knob('id_rep').getValue()] = 0
        ids  = list(ids.keys())


        return ids


    def get_placeholders(self):
        placeholders = super().get_placeholders()
        return placeholders




    
    def delete_placeholder(self, placeholder):
        #  min_x, min_y , max_x, max_y = get_extremes(selectedNodes)
        node = placeholder.data['node']
        lastLoaded = placeholder.data['last_loaded']

        if len(lastLoaded) > 0:
            if 'last_loaded' in node.knobs().keys():
                for s in node.knob('last_loaded').values():
                    n = nuke.toNode(s)
                    try :
                        delete_placeholder_attributes(n)
                    except :
                        pass

            lastLoaded_names = []
            for l in lastLoaded :
                lastLoaded_names.append(l.name())
            imprint(node, {'last_loaded' : lastLoaded_names})
            
            for n in lastLoaded :
                refresh_node(n)
                refresh_node(node)
                if 'builder_type' not in n.knobs().keys():
                    imprint(n, get_placeholder_attributes(node, enumerate= True))
                    imprint(n, {'is_placeholder' : False})
                    hide_placeholder_attributes(n)
                    n.knob('is_placeholder').setVisible(False)
                    imprint(n, {'x' : node.xpos(), 'y' : node.ypos()})
                    n.knob('x').setVisible(False)
                    n.knob('y').setVisible(False)
        nuke.delete(node)
        
                
                


class NukePlaceholder(AbstractPlaceholder):
    """Concrete implementation of AbstractPlaceholder for Nuke

    """

    optional_attributes = {'asset', 'subset', 'hierarchy'}

    def get_data(self, node):
        user_data = dict()
        for attr in self.attributes.union(self.optional_attributes):
            dictKnobs = node.knobs()
            if attr in dictKnobs.keys() :
                user_data[attr] = dictKnobs[attr].getValue()
        user_data['node'] = node
        if 'nodes_toReplace' in dictKnobs.keys() :
            names = dictKnobs['nodes_toReplace'].values()
            nodes = []
            for name in names :
                nodes.append(nuke.toNode(name))
            user_data['nodes_toReplace'] = nodes
        else :
            user_data['nodes_toReplace'] = [node]

        if 'nb_children' in dictKnobs.keys() :
            user_data['nb_children'] = int(dictKnobs['nb_children'].getValue())
        else :
            user_data['nb_children'] = 0
        if 'siblings' in dictKnobs.keys() :
            print(' \n /*/*/ ',dictKnobs['siblings'])
            user_data['siblings'] = dictKnobs['siblings'].values()
        else :
            user_data['siblings'] = []

        fullName = node.fullName()
        user_data['group_name'] = fullName.rpartition('.')[0]
        user_data['last_loaded'] = []

        self.data = user_data

    def parent_in_hierarchy(self, containers):
        return 




    def clean(self):


        reset_selection() #deselect all selected nodes


        node = self.data['node']

        # use of autoplace snap to be sure that we have the right values (updated) of screenWidth and screenHeight



        selectedNodes = [] 
        nodes_loaded = list(set(nuke.allNodes())-set(self.data["nodes_init"])) # getting the last nodes added

        for n in nodes_loaded :
            n.setSelected(True)
            refresh_node(n)
            selectedNodes.append(n)


        groupName = self.data['group_name']

        if (len(groupName) > 0):
            # new_node.setSelected(True)
            nuke.nodeCopy("%clipboard%")
            for n in nuke.selectedNodes():
                nuke.delete(n)
            group = nuke.toNode(groupName)
            group.begin()
            nuke.nodePaste("%clipboard%")
            for n in nuke.selectedNodes():

                n.setSelected(True)
                refresh_node(n)
                selectedNodes.append(n)

       

        selectedNodes = nuke.selectedNodes()
        self.data['last_loaded'] = selectedNodes
        reset_selection()
        input, output = get_io(selectedNodes)
       
        copies = None

        #positioning of the loaded nodes
        min_x, min_y , max_x, max_y = get_extremes(selectedNodes)
        
        for n in selectedNodes :
            xpos = (n.xpos() - min_x) + node.xpos()
            ypos = (n.ypos() - min_y) + node.ypos()
            n.setXYpos(xpos, ypos)


        # save the id of representation for all imported nodes
        d =  {"id_rep" : str(self.data['_id'])}
        
        for n in selectedNodes :
            if 'builder_type' not in n.knobs().keys():
                    imprint(n, d)
                    n.knob('id_rep').setVisible(False)

        # fix the problem of Z-order
        orders_bd = []
        for n in selectedNodes :
            if isinstance(n,nuke.BackdropNode) :
                orders_bd.append(n.knob("z_order").getValue())
        
        if len(orders_bd) > 0 :

            min_order = min(orders_bd)
            siblings = self.data["siblings"]

            orders_sib = []
            for s in siblings :
                n = nuke.toNode(s) 
                if isinstance(n,nuke.BackdropNode) :
                    orders_sib.append(n.knob("z_order").getValue())
            if len(orders_sib) > 0:
                max_order = max(orders_sib)
                for n in selectedNodes :
                    if isinstance(n,nuke.BackdropNode) :
                        n.knob("z_order").setValue(n.knob("z_order").getValue() + max_order-min_order + 1)



        if  self.data['nb_children'] == 0  :

            #Adjust backdrop dimensions and node positions by getting the difference of dimensions between what was
            diff_y = max_y - min_y - node.screenHeight() # difference of heights
            diff_x = max_x - min_x - node.screenWidth() # difference of widths


            if diff_y > 0 or diff_x > 0 :
                for n in nuke.allNodes() :
                    if n != node and n not in selectedNodes :
                        imprint(n, {'x_init' : n.xpos(), 'y_init' : n.ypos()})
                        n.knob('x_init').setVisible(False)
                        n.knob('y_init').setVisible(False)
                        if 'bdwidth' in n.knobs().keys():
                            imprint(n, {'w_init' : n.screenWidth(), 'h_init' : n.screenHeight()})
                            n.knob('w_init').setVisible(False)
                            n.knob('h_init').setVisible(False)
                        
                        if not isinstance(n, nuke.BackdropNode) or isinstance(n, nuke.BackdropNode) and node not in n.getNodes():
                            if  n.xpos()+n.screenWidth() >= node.xpos() + node.screenWidth():

                                n.setXpos(n.xpos() + diff_x)
                            print(n.screenHeight(), n.name())



                            if  n.ypos() + n.screenHeight()  >= node.ypos() + node.screenHeight() :
                                n.setYpos(n.ypos() + diff_y)


                        else :
                            width = n.knob("bdwidth").getValue()
                            height = n.knob("bdheight").getValue()
                            n.knob("bdwidth").setValue(width + diff_x)
                            n.knob("bdheight").setValue(height + diff_y)

           





            reset_selection()

            for n in node.dependent():
                for i in range(n.inputs()):
                    if n.input(i) == node:
                        n.setInput(i,output)

            for n in node.dependencies():
                    for i in range(node.inputs()):
                        if node.input(i) == n:
                            input.setInput(0,n)

            for n in selectedNodes:
                if "builder_type" in n.knobs().keys() and ( 'is_placeholder' not in  n.knobs().keys() or  'is_placeholder' in  n.knobs().keys() \
                    and n.knob('is_placeholder').value() ):
                    siblings_nodes = list(set(selectedNodes) - set([n]))
                    siblings_name = []
                    for s in siblings_nodes:
                        siblings_name.append(s.name())
                    siblings = {"siblings":siblings_name}
                    imprint(n, siblings)

            self.data['nodes_toReplace'] = selectedNodes

        elif len(self.data['siblings']) > 0 :
            siblings = self.data['siblings']
            copies ={}
            siblings_node = []
            new_nodes = []


            #creating copies of the palce_holder siblings (the ones who were loaded with it) for the new nodes added 
            new_nodes_name = []
            for s in siblings:
                n = nuke.toNode(s)
                refresh_node(n)

                siblings_node.append(n)
                reset_selection()
                n.setSelected(True)
                print("heeeeeeight", n.screenHeight())
                nuke.nodeCopy("%clipboard%")
                reset_selection()
                nuke.nodePaste("%clipboard%")
                new_node = nuke.selectedNodes()[0]
                print("heeeeeeight2", new_node.screenHeight())
                x_init = int(new_node.knob('x_init').getValue())
                y_init = int(new_node.knob('y_init').getValue())
                new_node.setXYpos(x_init, y_init)
                if isinstance(new_node, nuke.BackdropNode) :
                    w_init = new_node.knob('w_init').getValue()
                    h_init = new_node.knob('h_init').getValue()
                    new_node.knob('bdwidth').setValue(w_init)
                    new_node.knob('bdheight').setValue(h_init)
                    refresh_node(n)
                    # print("heeeeeeight2", new_node.screenHeight())


                # new_node.setXYpos(n.xpos(),n.ypos())
                if 'id_rep' in n.knobs().keys():
                    n.removeKnob(n.knob('id_rep'))
                new_nodes.append(new_node)
                new_nodes_name.append(new_node.name())
                copies[s] = new_node


            min_xxx, min_yyy , max_xxx, max_yyy = get_extremes(selectedNodes)
            diff_y = max_yyy - min_yyy - node.screenHeight() # difference of heights
            diff_x = max_xxx - min_xxx - node.screenWidth() # difference of widths


            if diff_y > 0 or diff_x > 0 :
                for n in new_nodes :
                    if not isinstance(n, nuke.BackdropNode) or isinstance(n, nuke.BackdropNode) and node not in n.getNodes():
                        if  n.xpos()+n.screenWidth() >= node.xpos() + node.screenWidth():
                            n.setXpos(n.xpos() + diff_x)

                        if  n.ypos() + n.screenHeight()  >= node.ypos() + node.screenHeight() :
                            n.setYpos(n.ypos() + diff_y)

                    else :
                        width = n.knob("bdwidth").getValue()
                        height = n.knob("bdheight").getValue()
                        n.knob("bdwidth").setValue(width + diff_x)
                        n.knob("bdheight").setValue(height + diff_y)

                    refresh_node(n)

            node.removeKnob(node.knob('siblings'))
            imprint(node, {'siblings' : new_nodes_name})



            inp, out = get_io(siblings_node)
            inp_copy, out_copy = (copies[inp.name()], copies[out.name()])


            for node_init in siblings_node :
                if node_init != out :
                    node_copy = copies[node_init.name()]
                    for n in node_init.dependent():
                        for i in range(n.inputs()):
                            if n.input(i) == node_init:
                                if n in siblings_node:
                                    copies[n.name()].setInput(i, node_copy)
                                else :
                                    input.setInput(0,node_copy)

                    for n in node_init.dependencies():
                        for i in range(node_init.inputs()):
                            if node_init.input(i) == n:
                                if node_init == inp :
                                    inp_copy.setInput(i,n)
                                elif n in siblings_node:
                                    node_copy.setInput(i, copies[n.name()])
                                else :
                                    node_copy.setInput(i, output)

            inp.setInput(0, out_copy)


            
            min_xx , min_yy , max_xx , max_yy = get_extremes(new_nodes)
            minX, _ , maxX, _ = get_extremes(siblings_node)
            offset_y = max_yy-min_yy +20
            offset_x = abs(max_xx - min_xx - maxX + minX)
            
            for n in nuke.allNodes():


                if n.ypos() >= min_yy and n not in selectedNodes+new_nodes and n != node :
                    n.setYpos(n.ypos() + offset_y)
                    # if 'x' in n.knobs().keys() :
                    #     n.removeKnob(n.knob('x'))
                    #     n.removeKnob(n.knob('y'))
                    #     imprint(n, {'x' : node.xpos() + offset_x, 'y' : node.ypos() + offset_y})

                if isinstance(n, nuke.BackdropNode) and set(new_nodes) <= set(n.getNodes()) :
                    height = n.knob("bdheight").getValue()
                    n.knob("bdheight").setValue(height + offset_y)
                    width = n.knob("bdwidth").getValue()
                    n.knob("bdwidth").setValue(width + offset_x)

            new_siblings = []
            for n in new_nodes :
                new_siblings.append(n.name())
            self.data['siblings'] = new_siblings

        else :
            xpointer, ypointer = find_free_space_to_paste_nodes(
                selectedNodes, direction="bottom", offset=200
            )
            n = nuke.createNode("NoOp")
            reset_selection()
            nuke.delete(n)
            for n in selectedNodes :
                xpos = (n.xpos() - min_x) + xpointer
                ypos = (n.ypos() - min_y) + ypointer
                n.setXYpos(xpos, ypos)

       
        self.data['nb_children'] += 1 
        reset_selection()
        nuke.root().begin() # go back to root group


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
            "Builder was looking for :\n{attributes}".format(
                attributes="\n".join([
                    "{}: {}".format(key.title(), value)
                    for key, value in self.data.items()]
                )
            )
        )
