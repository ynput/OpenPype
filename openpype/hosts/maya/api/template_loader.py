from openpype.lib.abstract_load_template import AbstractTemplateLoader
from maya import cmds


ATTRIBUTES = ['builder_type', 'representation', 'families',
              'repre_name', 'asset', 'hierarchy', 'loader', 'order']


class TemplateLoader(AbstractTemplateLoader):

    def import_template(self, path):
        self.newNodes = cmds.file(path, i=True, returnNewNodes=True)

    @staticmethod
    def get_template_nodes():
        attribute_list = cmds.ls('*.builder_type', long=True)
        return [attr.rpartition('.')[0] for attr in attribute_list]

    def placeholderize(self, node):
        return self._get_all_user_data_on_node(node)

    def is_placeholder_context(self, placeholder):
        return placeholder['builder_type'] == "context_asset"

    @staticmethod
    def get_valid_representations_id_for_placeholder(
            representations, placeholder):
        if len(representations) < 1:
            return []

        repres = [r['_id'] for rep in representations for r in rep if (
            placeholder['families'] == r['context']['family']
            and placeholder['repre_name'] == r['context']['representation']
            and placeholder['representation'] == r['context']['subset']
        )]

        if len(repres) < 1:
            raise ValueError(
                "No representation found for {} with:\n"
                "representation : {}\n"
                "representation name : {}\n"
                "Are you sure representations have been published ?".format(
                    placeholder['builder_type'],
                    placeholder['representation'],
                    placeholder['repre_name']))
        return repres

    @staticmethod
    def switch(containers, placeholder):
        node = placeholder['node']
        nodeParent = cmds.ls(node, long=True)[0].rpartition('|')[0]
        if cmds.nodeType(node) != 'transform':
            nodeParent = nodeParent.rpartition('|')[0]

        child = map(lambda x: x.replace(
            '__', '_:').replace('_CON', ''), containers)
        cmds.parent(child, nodeParent)

    @staticmethod
    def clean_placeholder(placeholder):
        node = placeholder['node']
        cmds.delete(node)

    @staticmethod
    def is_valid_placeholder(node):
        missing_attributes = [attr for attr in ATTRIBUTES
                              if not cmds.attributeQuery(
                                  attr, node=node, exists=True)]
        if missing_attributes:
            print("Ignoring '{}': Invalid template placeholder. Node miss \
                attribute : {}".format(node, ", ".join(missing_attributes)))
            return False

        return True

    @staticmethod
    def _get_placeholder_loader_name(placeholder):
        return placeholder['loader']

    @staticmethod
    def _get_node_data(node):
        user_data = dict()
        for attr in ATTRIBUTES:
            user_data[attr] = cmds.getAttr(
                '{}.{}'.format(node, attr),
                asString=True)
        user_data['node'] = node

        return user_data
