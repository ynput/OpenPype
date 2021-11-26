import openpype.lib

from maya import cmds

from openpype.lib.build_template_exceptions import TemplateAlreadyImported

PLACEHOLDER_SET = 'PLACEHOLDERS_SET'


class MayaTemplateLoader(openpype.lib.AbstractTemplateLoader):
    """Concrete implementation of AbstractTemplateLoader for maya

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
        if cmds.objExists(PLACEHOLDER_SET):
            raise TemplateAlreadyImported(
                "Build template already loaded\n"
                "Clean scene if needed (File > New Scene)")

        cmds.sets(name=PLACEHOLDER_SET, empty=True)
        self.new_nodes = cmds.file(path, i=True, returnNewNodes=True)
        cmds.setAttr(PLACEHOLDER_SET + '.hiddenInOutliner', True)

        return True

    def template_already_imported(self, err_msg):
        clearButton = "Clear scene and build"
        updateButton = "Update template"
        abortButton = "Abort"

        title = "Scene already builded"
        message = (
            "It's seems a template was already build for this scene.\n"
            "Error message reveived :\n\n\"{}\"".format(err_msg))
        buttons = [clearButton, updateButton, abortButton]
        defaultButton = clearButton
        cancelButton = abortButton
        dismissString = abortButton
        answer = cmds.confirmDialog(
            t=title,
            m=message,
            b=buttons,
            db=defaultButton,
            cb=cancelButton,
            ds=dismissString)

        if answer == clearButton:
            cmds.file(newFile=True, force=True)
            self.import_template(self.template_path)
            self.populate_template()
        elif answer == updateButton:
            self.update_template()
        elif answer == abortButton:
            return

    @staticmethod
    def get_template_nodes():
        attributes = cmds.ls('*.builder_type', long=True)
        return [attribute.rpartition('.')[0] for attribute in attributes]

    def get_loaded_containers_by_id(self):
        containers = cmds.sets('AVALON_CONTAINERS', q=True)
        return {cmds.getAttr(container + '.representation'): container
                for container in containers}


class MayaPlaceholder(openpype.lib.AbstractPlaceholder):
    """Concrete implementation of AbstractPlaceholder for maya

    """

    optional_attributes = {'asset', 'subset', 'hierarchy'}

    def get_data(self, node):
        user_data = dict()
        for attr in self.attributes.union(self.optional_attributes):
            attribute_name = '{}.{}'.format(node, attr)
            if not cmds.attributeQuery(attr, node=node, exists=True):
                print("{} not found".format(attribute_name))
                continue
            user_data[attr] = cmds.getAttr(
                attribute_name,
                asString=True)
        user_data['parent'] = (
            cmds.getAttr(node + '.parent', asString=True)
            or node.rpartition('|')[0])
        user_data['node'] = node.rpartition('|')[2]

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

        if cmds.listRelatives(node, p=True):
            cmds.parent(node, world=True)
        cmds.sets(node, addElement=PLACEHOLDER_SET)
        cmds.hide(node)
        cmds.setAttr(node + '.hiddenInOutliner', True)
