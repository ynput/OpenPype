import avalon
import importlib

concrete_loaders_modules = {
    'maya': 'openpype.hosts.maya.api.template_loader'
}


def build_workfile_template(self):
    host_name = avalon.io.Session['AVALON_APP']
    module_path = concrete_loaders_modules.get(host_name, None)

    if not module_path:
        raise ValueError("Template not found for host '{}'".format(host_name))

    module = importlib.import_module(module_path)
    if not hasattr(module, 'TemplateLoader'):
        raise ValueError(
            "Linked module '{}' does not "
            "implement a template loader".format(module_path))
    if not hasattr(module, 'Placeholder'):
        raise ValueError(
            "Linked module '{}' does not "
            "implement a placeholder template".format(module_path))
    concrete_loader = module.TemplateLoader
    concrete_template_loader = concrete_loader(module.Placeholder)
    concrete_template_loader.process()
