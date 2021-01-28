import pype.hosts.maya.plugin


class AbcLoader(pype.hosts.maya.plugin.ReferenceLoader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["animation",
                "camera",
                "pointcache"]
    representations = ["abc"]

    label = "Reference animation"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        # Prevent identical alembic nodes from being shared
        # Create unique namespace for the cameras

        # Get name from asset being loaded
        # Assuming name is subset name from the animation, we split the number
        # suffix from the name to ensure the namespace is unique
        name = name.split("_")[0]
        namespace = maya.unique_namespace("{}_".format(name),
                                          format="%03d",
                                          suffix="_abc")

        # hero_001 (abc)
        # asset_counter{optional}

        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        # load colorbleed ID attribute
        self[:] = nodes

        return nodes
