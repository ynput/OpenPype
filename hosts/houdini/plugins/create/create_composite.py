from openpype.hosts.houdini.api import plugin


class CreateCompositeSequence(plugin.Creator):
    """Composite ROP to Image Sequence"""

    label = "Composite (Image Sequence)"
    family = "imagesequence"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreateCompositeSequence, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        # Type of ROP node to create
        self.data.update({"node_type": "comp"})

    def _process(self, instance):
        """Creator main entry point.

        Args:
            instance (hou.Node): Created Houdini instance.

        """
        parms = {"copoutput": "$HIP/pyblish/%s.$F4.exr" % self.name}

        if self.nodes:
            node = self.nodes[0]
            parms.update({"coppath": node.path()})

        instance.setParms(parms)

        # Lock any parameters in this list
        to_lock = ["prim_to_detail_pattern"]
        for name in to_lock:
            try:
                parm = instance.parm(name)
                parm.lock(True)
            except AttributeError:
                # missing lock pattern
                self.log.debug(
                    "missing lock pattern {}".format(name))
