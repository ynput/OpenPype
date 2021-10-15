from openpype.plugins.load.abstract_load_template import AbstractTemplateLoader
import importlib

cmds = None
def init_cmds():
    global cmds
    if cmds is None:
        cmds = importlib.import_module('maya').cmds

class TemplateLoader(AbstractTemplateLoader):

    def __init__(self):
        init_cmds()
        super(TemplateLoader, self).__init__()

    def import_template(self, path):
        self.newNodes = cmds.file(path, i=True, returnNewNodes=True)#Find a way to instantiate only once

    def _get_all_nodes_with_attribute(self, attribute_name):
        attribute_list = cmds.ls('*.{}'.format(attribute_name), long=True)
        return [attr.rpartition('.')[0] for attr in attribute_list]

    def _get_all_user_data_on_node(self, node):
        all_attributes = cmds.listAttr(node, userDefined=1)

        user_data = {}
        for attr in all_attributes:
            user_data[attr] = cmds.getattr('{}.{}'.format(node, attr))

        return user_data

    def get_template_nodes(self): # Get templates nodes objects ? How ? Agnostic
        context_nodes = self._get_all_nodes_with_attribute('current_context_builder') #attribute name must be a variable
        asset_nodes = self._get_all_nodes_with_attribute('linked_asset_builder') #attribute name must be a variable

        return context_nodes + asset_nodes

    def get_loader_data(self):
        loaders_data = {}
        for node in self.get_placeholders():
            loaders_data[node] = self._get_all_user_data_on_node(node)

        return loaders_data

    def switch(self, container, node):
        nodeParent = cmds.ls(node, long=True)[0].rpartition('|')[0]
        if cmds.nodeType(node) != 'transform':
            nodeParent = nodeParent.rpartition('|')[0]
        child = map(lambda x: x.replace('__', '_:').replace('_CON', ''), container)
        cmds.parent(child, nodeParent)
        cmds.delete(node)

    @staticmethod
    def is_valid_placeholder(node):
        if not cmds.attributeQuery('Test', node=node, exists=True):
            print("Ignoring '{}': Invalid template placeholder".format(node))
            return True
        return True

## TODO: Replace by get_loader_data
    @staticmethod
    def get_is_context_asset(node):
        return not cmds.getAttr(node+".linked_asset_builder")

    @staticmethod
    def get_loader(node):
        return cmds.getAttr(node+".loader")

    @staticmethod
    def get_representation_type(node):
        return cmds.getAttr(node+".repre_name")

    @staticmethod
    def get_family(node):
        return cmds.getAttr(node+".families")

    @staticmethod
    def get_subset(node):
        return cmds.getAttr(node+".representation")

    @staticmethod
    def get_name(node):
        return cmds.getAttr(node+".asset")

    @staticmethod
    def get_order(node):
        return cmds.getAttr(node+".order")