from avalon import api


class SetDressAlembicLoader(api.Loader):
    """Load the setdress as alembic"""

    families = ["colorbleed.setdress"]
    representations = ["abc"]

    label = "Load Alembic"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        import maya.cmds as cmds
        from avalon import maya

        namespace = maya.unique_namespace("{}_".format(name),
                                          format="%03d",
                                          suffix="_abc")

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        self[:] = nodes
