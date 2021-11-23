import openpype
from openpype.lib import AbstractPlaceholder, AbstractTemplateLoader

import importlib

module_path_format = 'openpype.hosts.{host}.api.template_loader'


def build_workfile_template(self):
    host_name = openpype.avalon.registered_host().__name__.partition('.')[2]
    module_path = module_path_format.format(host=host_name)
    module = importlib.import_module(module_path)
    if not module:
        raise MissingHostTemplateModule(
            "No template loader found for host {}".format(host_name))

    template_loader_class = openpype.lib.classes_from_module(
        AbstractTemplateLoader, module)
    template_placeholder_class = openpype.lib.classes_from_module(
        AbstractPlaceholder, module)

    if not template_loader_class:
        raise MissingTemplateLoaderClass()
    template_loader_class = template_loader_class[0]

    if not template_placeholder_class:
        raise MissingTemplatePlaceholderClass()
    template_placeholder_class = template_placeholder_class[0]

    template_loader = template_loader_class(template_placeholder_class)
    template_loader.process()

class MissingHostTemplateModule(Exception):
    """Error raised when expected module does not exists"""
    pass

class MissingTemplatePlaceholderClass(Exception):
    """ """
    pass

class MissingTemplateLoaderClass(Exception):
    """ """
    pass