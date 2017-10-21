from avalon import api


class SetDressRebuild(api.Loader):

    families = ["colorbleed.setdress"]
    representations = ["json"]

    label = "Rebuild Set Dress"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        import setdress_api

        containers = setdress_api.load_package(filepath=self.fname,
                                               name=name,
                                               namespace=namespace)

        self[:] = containers
