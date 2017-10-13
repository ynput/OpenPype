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

        from maya import cmds
        import avalon.maya as amaya

        context_ns = context["subset"]["name"]
        with amaya.maintained_selection():
            file_nodes = cmds.file(self.fname,
                                   namespace=context_ns,
                                   reference=True,
                                   returnNewNodes=True,
                                   groupReference=True,
                                   groupName="{}:{}".format(context_ns, name))

        self[:] = file_nodes
