from avalon import api


class AnimationLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation",
                "colorbleed.camera",
                "colorbleed.pointcache"]
    label = "Reference animation"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        import maya.cmds as cmds

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        self[:] = nodes


class SetDressAlembicLoader(api.Loader):
    """Load the setdress as alembic"""

    families = ["colorbleed.setdress"]
    label = "Reference Alembic"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        import maya.cmds as cmds

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        self[:] = nodes
