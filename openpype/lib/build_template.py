import avalon
import importlib

concrete_loaders_modules = {
    'maya': 'openpype.hosts.maya.api.template_loader'
}


class BuildWorkfileTemplate:
    # log = logging.getLogger("BuildWorkfile")

    def process(self):
        dcc = avalon.io.Session['AVALON_APP']
        module_path = concrete_loaders_modules.get(dcc, None)

        if not module_path:
            raise ValueError("Template not found for DCC '{}'".format(dcc))

        module = importlib.import_module(module_path)
        if not hasattr(module, 'TemplateLoader'):
            raise ValueError(
                "Linked module '{}' does not implement a template loader".format(module_path))
        if not hasattr(module, 'Placeholder'):
            raise ValueError(
                "Linked module '{}' does not implement a placeholder template".format(module_path))
        reload(module)
        concrete_loader = module.TemplateLoader
        concrete_loader(module.Placeholder)
