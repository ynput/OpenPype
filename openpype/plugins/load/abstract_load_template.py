import avalon
from openpype.settings import get_project_settings
from maya import cmds


class AbstractTemplateLoader:

    def __init__(self):
        loaders_by_name = {}
        for loader in avalon.api.discover(avalon.api.Loader):
            loader_name = loader.__name__
            if loader_name in loaders_by_name:
                raise KeyError(
                    "Duplicated loader name {0}!".format(loader_name)
                )
            loaders_by_name[loader_name] = loader

        # Skip if there are any loaders
        if not loaders_by_name:
            self.log.warning("There are no registered loaders.")
            return

        self.import_template(self.template_path)

        placeholders = (
            self.placeholderize(node) for node
            in self.get_template_nodes()
            if self.is_valid_placeholder(node)
        )

        loaded_containers = []
        for placeholder in placeholders:
            container = avalon.api.load(
                loaders_by_name[placeholder['loader']],
                repre["_id"],
                name=placeholder['name']
            )
            loaded_containers.append(container)

    @property
    def template_path(self):
        project_settings = get_project_settings(avalon.io.Session["AVALON_PROJECT"])
        #TODO: get task, get DCC
        for profile in project_settings['maya']['workfile_build']['profiles']: #get DCC
            if 'Modeling' in profile['task_types']: # Get tasktype
                return profile['path'] #Validate path
        raise ValueError("No matching profile found for task '{}' in DCC '{}'".format('Modeling', 'maya'))

    def import_template(self, template_path):
        """
        Import template in dcc

        Args:
            template_path (str): fullpath to current task and dcc's template file
        """
        raise NotImplementedError

    def get_template_nodes(self):
        raise NotImplementedError

    def populate_template(self, nodes):
        raise NotImplementedError

    def placeholderize(self, node):
        return {
            'loader': self.get_placeholder_loader(node),
            'type': self.get_placeholder_type(node),
            'node': node,
            'name': node,
        }

    @staticmethod
    def is_valid_placeholder(node):
        raise NotImplementedError

    @staticmethod
    def get_placeholder_loader(node):
        raise NotImplementedError

    @staticmethod
    def get_placeholder_type(node):
        raise NotImplementedError

class TemplateLoader(AbstractTemplateLoader):
    def import_template(self, path):
        self.newNodes = cmds.file(path, i=True, returnNewNodes=True)#Find a way to instantiate only once

    def get_template_nodes(self): # Get templates nodes objects ? How ? Agnostic
        #cmds.listAttribute('')
        return cmds.ls(self.newNodes, type='locator') #filter by correct placeholders only

    def switch(self, placeholder): # Probably useless
        print(placeholder['loader'])

    @staticmethod
    def is_valid_placeholder(node):
        if not cmds.attributeQuery('Test', node=node, exists=True):
            print("Ignoring '{}': Invalid template placeholder".format(node))
            return True
        return True

    @staticmethod
    def get_placeholder_loader(node):
        return cmds.attributeQuery('loader', node=node)

    @staticmethod
    def get_placeholder_type(node):
        return cmds.attributeQuery('type', node=node)
