import avalon
import importlib

def get_concrete_template_loader():
    concrete_loaders_modules = {
        'maya': 'openpype.hosts.maya.api.template_loader'
    }

    dcc = avalon.io.Session['AVALON_APP']
    module_path = concrete_loaders_modules.get(dcc, None)

    if not module_path:
        raise ValueError("Template not found for DCC '{}'".format(dcc))

    module = importlib.import_module(module_path)
    if not hasattr(module, 'TemplateLoader'):
        raise ValueError("Linked module '{}' does not implement a template loader".format(module_path))

    concrete_loader = module.TemplateLoader

    return concrete_loader


class BuildWorkfileTemplate:
    # log = logging.getLogger("BuildWorkfile")

    def process(self):
        containers = self.build_workfile()

        return containers

    def build_workfile(self):
        concrete = get_concrete_template_loader()
        instance = concrete()
