from openpype.hosts.houdini.api import plugin


class CreateAlembicCamera(plugin.Creator):
    """Single baked camera from Alembic ROP"""

    name = "camera"
    label = "Camera (Abc)"
    family = "camera"
    icon = "camera"

    def __init__(self, *args, **kwargs):
        super(CreateAlembicCamera, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        # Set node type to create for output
        self.data.update({"node_type": "alembic"})

    def _process(self, instance):
        """Creator main entry point.

        Args:
            instance (hou.Node): Created Houdini instance.

        """
        parms = {
            "filename": "$HIP/pyblish/%s.abc" % self.name,
            "use_sop_path": False,
        }

        if self.nodes:
            node = self.nodes[0]
            path = node.path()
            # Split the node path into the first root and the remainder
            # So we can set the root and objects parameters correctly
            _, root, remainder = path.split("/", 2)
            parms.update({"root": "/" + root, "objects": remainder})

        instance.setParms(parms)

        # Lock the Use Sop Path setting so the
        # user doesn't accidentally enable it.
        instance.parm("use_sop_path").lock(True)
        instance.parm("trange").set(1)
