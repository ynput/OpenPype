import avalon
from openpype.hosts.maya.plugins.init.template_loader import TemplateLoader as maya_TemplateLoader


def get_concrete_template_loader():
    concrete_loaders = {
        'maya': maya_TemplateLoader
    }

    dcc = avalon.io.Session['AVALON_APP']
    loader = concrete_loaders.get(dcc)
    if not loader:
        raise ValueError('DCC not found for template')
    return loader


class BuildWorkfileTemplate:
    # log = logging.getLogger("BuildWorkfile")

    def process(self):
        containers = self.build_workfile()

        return containers

    def build_workfile(self):
        concrete = get_concrete_template_loader()
        instance = concrete()
