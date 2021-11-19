from openpype.lib.abstract_load_template import AbstractTemplateLoader,\
    AbstractPlaceholder
from maya import cmds

PLACEHOLDER_SET = 'PLACEHOLDERS_SET'


class TemplateLoader(AbstractTemplateLoader):
    """Concrete implementation of AbstractTemplateLoader for maya

    """

    def import_template(self, path):
        """Import template into current scene.
        Block if a template is already loaded.

        Args:
            path (str): A path to current template (usually given by
            get_template_path implementation)

        Raises:
            ValueError: "Build already generated"
        """
        if cmds.objExists(PLACEHOLDER_SET):
            raise ValueError("Build already generated. Please clean scene if "
                             "you really want to rebuild. (File>New Scene)")
        cmds.sets(name=PLACEHOLDER_SET, empty=True)
        self.new_nodes = cmds.file(path, i=True, returnNewNodes=True)
        cmds.setAttr(PLACEHOLDER_SET + '.hiddenInOutliner', True)

    @staticmethod
    def get_template_nodes():
        attributes = cmds.ls('*.builder_type', long=True)
        return [attribute.rpartition('.')[0] for attribute in attributes]


class Placeholder(AbstractPlaceholder):
    """Concrete implementation of AbstractPlaceholder for maya

    """

    optional_attributes = {'asset', 'subset', 'hierarchy'}

    def get_data(self, node):
        user_data = dict()
        for attr in self.attributes:
            attribute_name = '{}.{}'.format(node, attr)
            if not cmds.attributeQuery(attr, node=node, exists=True):
                print("{} not found".format(attribute_name))
                continue
            user_data[attr] = cmds.getAttr(
                attribute_name,
                asString=True)
        for attr in self.optional_attributes:
            attribute_name = 'optional_settings.{}'.format(node, attr)
            if not cmds.attributeQuery(attribute_name, node=node, exists=True):
                continue
            user_data[attr] = cmds.getAttr(
                node + '.' + attribute_name,
                asString=True)
        user_data['parent'], _, user_data['node'] = node.rpartition('|')

        self.data = user_data

    def parent_in_hierarchy(self, containers):
        """Parent loaded container to placeholder's parent
        ie : Set loaded content as placeholder's sibling

        Args:
            containers (String): Placeholder loaded containers
        """
        roots = [container.partition('__')[0] + "_:_GRP"
                 for container in containers]
        cmds.parent(roots, self.data['parent'])

    def clean(self):
        """Hide placeholder
        parent them to root
        add them to placeholder set
        and register placeholder's parent
        to keep placeholder info available
        for future use
        """
        node = self.data['node'].rpartition('|')[2]
        cmds.setAttr(node + '.parent', self.data['parent'], type='string')

        cmds.parent(node, world=True)
        cmds.sets(node, addElement=PLACEHOLDER_SET)
        cmds.hide(node)
        cmds.setAttr(node + '.hiddenInOutliner', True)
