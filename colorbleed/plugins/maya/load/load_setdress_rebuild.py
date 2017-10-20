import site

from avalon import api

site.addsitedir(r"C:\Users\User\Documents\development\research\setdress")


class SetDressRebuild(api.Loader):

    families = ["colorbleed.setdress"]
    representations = ["json"]

    label = "Rebuild Set Dress"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        # Hack
        import sys

        p = r"C:\Users\User\Documents\development\research\setdress"
        if p not in sys.path:
            sys.path.insert(0, p)

        import loader
        reload(loader)

        containers = loader.load_package(filepath=self.fname,
                                         name=name,
                                         namespace=namespace)

        self[:] = containers
