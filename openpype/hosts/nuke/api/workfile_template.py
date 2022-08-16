import ast
import os
import nuke
import nukescripts

from openpype.pipeline import discover_legacy_creator_plugins
from openpype.api import Logger

log = Logger.get_logger(__name__)


class WorkfileTemplate():

    def __init__(self):
        pass

    def _get_op_nodes(self, selected_only=True):
        '''
        Returns list of Nuke nodes that are OP loaders or creators.

        Only returns nodes that have avalon:id knob
        Optionally returns node only if it is selected
        '''

        nodes = []
        for node in nuke.allNodes(recurseGroups=False):
            if "OpenpypeDataGroup" in node.knobs():
                try:
                    if not selected_only:
                        nodes.append(node)
                    elif node['selected'].value():
                        nodes.append(node)

                except NameError:
                    pass

        if len(nodes) == 0:
            log.warning('OP nodes not found')
        else:
            log.debug('OP nodes:')
            for node in nodes:
                log.debug(str(node['name'].value()))

        return nodes

    def _get_op_template_nodes(self):
        '''
        Returns list of Nuke nodes - templates for OP loaders or creators

        Only returns Template nodes, recognized by hidden knob is_op_template
        '''

        nodes = []
        for node in nuke.allNodes(filter='NoOp'):
            if "is_op_template" in node.knobs():
                nodes.append(node)

        return nodes

    def _get_connected_nodes(self, node):
        '''
        Returns a two-tuple of lists. Each list is made up of two-tuples in the
        form ``(index, nodeObj)`` where 'index' is an input index and 'nodeObj'
        is a Nuke node.

        The first list contains the inputs to 'node', where each 'index' is the
        input index of 'node' itself.

        The second contains its outputs, where each 'index' is
        the input index that is connected to 'node'.
        '''

        inputNodes = [(i, node.input(i)) for i in range(node.inputs())]
        outputNodes = []
        deps = nuke.dependentNodes(nuke.INPUTS | nuke.HIDDEN_INPUTS, node)
        for depNode in deps:
            for i in range(depNode.inputs()):
                if depNode.input(i) == node:
                    outputNodes.append((i, depNode))
        return (inputNodes, outputNodes)

    def _swap_nodes(self, targetNode, newNode):
        '''
        Mimics the Ctrl + Shift + drag-and-drop node functionality in Nuke.

        'targetNode': The node (or node name) to be replaced.
        'newNode': The node (or node name) that will replace it.
        '''
        if isinstance(targetNode, str):
            targetNode = nuke.toNode(targetNode)
        if isinstance(newNode, str):
            newNode = nuke.toNode(newNode)
        if not (isinstance(targetNode, nuke.Node) and
                isinstance(newNode, nuke.Node)):
            return

        source_node_width = newNode.screenWidth() / 2
        source_node_height = newNode.screenHeight() / 2
        target_node_width = targetNode.screenWidth() / 2
        target_node_height = targetNode.screenHeight() / 2
        width_offset = target_node_width - source_node_width
        height_offset = target_node_height - source_node_height
        sourcePos = (newNode.xpos(), newNode.ypos())
        targetPos = (targetNode.xpos() + width_offset,
                     targetNode.ypos() + height_offset)
        inputNodes, outputNodes = self._get_connected_nodes(targetNode)
        nukescripts.clear_selection_recursive()
        targetNode.setSelected(True)
        nuke.extractSelected()
        targetNode.setSelected(False)
        newNode.setXYpos(*targetPos)
        targetNode.setXYpos(*sourcePos)
        for inNode in inputNodes:
            newNode.setInput(*inNode)
        for index, node in outputNodes:
            node.setInput(index, newNode)

    def _make_temps_from_op_nodes(self, op_nodes):
        '''
        Converts OP nodes to template nodes

        Template Nodes store
            loader / Creator name
            OP node subset
            other selected knobs and their values as a string
            knob indicating that node is a template node
        '''

        # Selected knobs to be stored
        knobs_to_store = {
            'CreateWriteRender': [
                'publish', 'render', 'review',
                'deadlinePriority', 'deadlineChunkSize',
                'deadlineConcurrentTasks', 'suspend_publish'],
            'CreateWritePrerender': [
                'publish', 'render', 'review',
                'deadlinePriority', 'deadlineChunkSize',
                'deadlineConcurrentTasks', 'suspend_publish',
                'channels', 'first', 'last', 'use_limit'],
            'CreateWriteStill': [
                'publish', 'render', 'review',
                'deadlinePriority', 'deadlineChunkSize',
                'deadlineConcurrentTasks', 'suspend_publish'
                'channels', 'first', 'last', 'use_limit'],
            'LoadClip':
                ['avalon:version', 'avalon:frameStart', 'avalon:frameEnd'],
            'LoadEffectsInputProcess':
                ['name']
        }

        node_count = 0
        for node in op_nodes:
            node_count += 1
            # Make knobs
            knob_tab = nuke.Tab_Knob('OP Template')
            knob_load_create = nuke.String_Knob('loaderCreator',
                                                'Loader/Creator')
            knob_is_creator = nuke.Boolean_Knob('is_op_creator', 'Creator')
            knob_subset = nuke.String_Knob('subset', 'Subset')
            knob_other = nuke.Multiline_Eval_String_Knob('other',
                                                         'Other')
            knob_is_template = nuke.Boolean_Knob('is_op_template',
                                                 'Is Template')
            knob_is_template.setValue(True)
            knob_is_template.setVisible(False)
            node_name = str(node['name'].value())

            # Loader or Creator?
            if str(node['avalon:id'].value()) == 'pyblish.avalon.container':
                # Node type is pyblish.avalon.container - Loader
                template_node = nuke.nodes.NoOp(tile_color='0xff7f00ff')
                load_create = str(node['avalon:loader'].value())
                knob_load_create.setText(load_create)
                knob_is_creator.setValue(False)
                knob_subset.setText(str(node['avalon:name'].value()))
                template_label = str(node['avalon:loader'].value())
                template_label += '\n' + str(node['avalon:name'].value())
            else:
                # Node type is pyblish.avalon.instance - Creator
                template_node = nuke.nodes.NoOp(tile_color='0xff3d00ff')
                try:
                    load_create = str(node['avalon:creator'].value())
                except NameError:
                    # Writing model via WriteGeo doesn't store creator
                    load_create = ''
                    if str(node['avalon:subset'].value()).startswith('model'):
                        load_create = 'CreateModel'
                knob_load_create.setText(load_create)
                knob_is_creator.setValue(True)
                knob_subset.setText(str(node['avalon:subset'].value()))
                template_label = str(node['avalon:subset'].value())

            template_node['name'].setValue('Template{}'.format(node_count))
            template_node['label'].setValue(template_label)

            # Store handpicked knobs and their values - from knobs_to_store
            to_store = {}
            if knobs_to_store.get(load_create):
                for knob_to_store in knobs_to_store[load_create]:
                    my_knob = node.knob(str(knob_to_store))
                    if my_knob:
                        try:
                            knob_type_num = nuke.knob(
                                my_knob.fullyQualifiedName(), type=True)
                            to_store[knob_to_store] = {
                                'value': node[knob_to_store].value(),
                                'type': knob_type_num
                            }
                        except NameError:
                            # Some knobs to be stored might not be present
                            log.debug('Node {}: knob to be stored not found'
                                      .format(node_name))

            knob_other.setText(str(to_store))
            # Add knobs to Template node
            template_node.addKnob(knob_tab)
            template_node.addKnob(knob_load_create)
            template_node.addKnob(knob_is_creator)
            template_node.addKnob(knob_subset)
            template_node.addKnob(knob_other)
            template_node.addKnob(knob_is_template)

            self._swap_nodes(node, template_node)
            nuke.delete(node)

    def _make_op_creator_nodes_from_temps(self):
        '''
        For each creator template creates OP node
        '''

        t_nodes = self._get_op_template_nodes()
        t_creators = [node for node in t_nodes 
                      if node['is_op_creator'].value()]
        asset = str(os.environ["AVALON_ASSET"])
        for temp_creator in t_creators:
            load_create = str(temp_creator['loaderCreator'].value())
            subset = str(temp_creator['subset'].value())

            # Get appropriate plugin class
            creator_plugin = None
            for creator in discover_legacy_creator_plugins():
                if str(creator.__name__) != load_create:
                    continue
                creator_plugin = creator

            if creator_plugin:
                creator_plugin(subset, asset).process()
            else:
                log.warning('Creator plugin {} not found'.format(load_create))

    def _template_connect(self):
        '''
        Swaps OP loaders or creators with corresponding template nodes,
        delete Template nodes
        '''

        op_nodes = self._get_op_nodes(selected_only=False)
        template_nodes = self._get_op_template_nodes()

        for one_template in template_nodes:
            load_create = str(one_template['loaderCreator'].value())
            subset = str(one_template['subset'].value())
            is_op_creator = bool(one_template['is_op_creator'].value())
            knob_dict = {}
            try:
                knob_dict = ast.literal_eval(
                    str(one_template['other'].value()))
            except ValueError:
                log.warning('Temp node {} knobs failed to parse.'.format(
                    one_template['name'].value()))

            target_node = None
            if is_op_creator:
                # it is a creator, compare subsets
                for node in op_nodes:
                    try:
                        if subset == str(node['avalon:subset'].value()):
                            target_node = node
                            break
                    except NameError:
                        pass
            else:
                # it is a loader, compare subset and loader name
                for node in op_nodes:
                    try:
                        if subset == str(node['avalon:name'].value()):
                            node_loader = str(node['avalon:loader'].value())
                            if load_create == node_loader:
                                target_node = node
                                break
                    except NameError:
                        pass

            if target_node:
                self._swap_nodes(one_template, target_node)
                for knob_name, knob in knob_dict.items():
                    try:
                        knob_value = str(knob['value'])
                        knob_type = int(knob['type'])
                        if knob_type == 3:
                            knob_value = int(knob_value)
                        elif knob_type == 6:
                            knob_value = bool(knob_value)
                        elif knob_type == 8:
                            knob_value = float(knob_value)
                        target_node[knob_name].setValue(knob_value)
                    except NameError:
                        pass
                nuke.delete(one_template)

        return True

    def create_template(self):

        # get OP nodes
        op_nodes = len(nuke.selectedNodes())
        if op_nodes == 0:
            # No nodes selected. Assume user wants to convert all OP nodes
            op_nodes = self._get_op_nodes(selected_only=False)
        else:
            # Some nodes selected.
            # Assume user wants to convert just selected nodes
            log.info("Templating only {} selected nodes".format(op_nodes))
            op_nodes = self._get_op_nodes(selected_only=True)

        # Convert OP nodes to template nodes
        self._make_temps_from_op_nodes(op_nodes)
        log.info("Template created. Please save to location specified\
                  by settings: workfile_builder - curstom_templates - path")

    def apply_template(self):
        # Make creators
        self._make_op_creator_nodes_from_temps()

        # Swap templates with loaders/creators
        # Delete templates
        self._template_connect()
