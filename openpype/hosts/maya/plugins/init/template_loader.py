from openpype.plugins.load.abstract_load_template import AbstractTemplateLoader
import importlib

cmds = None
def init_cmds():
    global cmds
    cmds = cmds or importlib.import_module('maya').cmds

ATTRIBUTES = ['asset_type', 'representation', 'families', 'repre_name', 'asset', 'hierarchy', 'loader', 'order']

class TemplateLoader(AbstractTemplateLoader):

    def __init__(self):
        init_cmds()
        super(TemplateLoader, self).__init__()

    def import_template(self, path):
        self.newNodes = cmds.file(path, i=True, returnNewNodes=True)


    def get_template_nodes(self):
        return self._get_all_nodes_with_attribute('asset_type')

    def placeholderize(self, node):
        return self._get_all_user_data_on_node(node)

    @staticmethod
    def get_valid_representations_id_for_placeholder(representations, placeholder):
        repres = [r['_id'] for rep in representations for r in rep if (
            placeholder['families'] == r['context']['family']
            and placeholder['repre_name'] == r['context']['representation']
            and placeholder['representation'] == r['context']['subset']
            )]

        if len(repres) <1:
            raise ValueError("No representation found for asset {} with:\n"
                  "family : {}\n"
                  "rerpresentation : {}\n"
                  "subset : {}\n".format(
                      placeholder['name'],
                      placeholder['family'],
                      placeholder['representation_type'],
                      placeholder['subset']
                      )
                    )
        return repres

    @staticmethod
    def switch(container, placeholder):
        node = placeholder['node']
        nodeParent = cmds.ls(node, long=True)[0].rpartition('|')[0]
        if cmds.nodeType(node) != 'transform':
            nodeParent = nodeParent.rpartition('|')[0]
        #TODO: Find a prettier solution
        child = map(lambda x: x.replace('__', '_:').replace('_CON', ''), container)
        cmds.parent(child, nodeParent)
        cmds.delete(node)

    @staticmethod
    def is_valid_placeholder(node):
        missing_attributes = [attr for attr in ATTRIBUTES if not cmds.attributeQuery(attr, node=node, exists=True)]
        if missing_attributes:
            print("Ignoring '{}': Invalid template placeholder. Node miss attribute : {}".format(node, ", ".join(missing_attributes)))
            return False

        return True

    @staticmethod
    def _get_placeholder_loader_name(placeholder):
         return placeholder['loader']

    @staticmethod
    def _get_all_nodes_with_attribute(attribute_name):
        attribute_list = cmds.ls('*.{}'.format(attribute_name), long=True)
        return [attr.rpartition('.')[0] for attr in attribute_list]

    @staticmethod
    def _get_node_data(node):
        all_attributes = cmds.listAttr(node, userDefined=True)

        user_data = {}
        for attr in all_attributes:
            if not attr in ATTRIBUTES:
                continue
            user_data[attr] = cmds.getAttr('{}.{}'.format(node, attr), asString=True)
        user_data['node'] = node

        return user_data