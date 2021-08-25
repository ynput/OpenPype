from openpype.hosts.houdini.api import plugin


class CreateUSD(plugin.Creator):
    """Universal Scene Description"""

    label = "USD (experimental)"
    family = "usd"
    icon = "gears"
    enabled = False

    def __init__(self, *args, **kwargs):
        super(CreateUSD, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "usd"})

    def _process(self, instance):
        """Creator main entry point.

        Args:
            instance (hou.Node): Created Houdini instance.

        """
        parms = {
            "lopoutput": "$HIP/pyblish/%s.usd" % self.name,
            "enableoutputprocessor_simplerelativepaths": False,
        }

        if self.nodes:
            node = self.nodes[0]
            parms.update({"loppath": node.path()})

        instance.setParms(parms)

        # Lock any parameters in this list
        to_lock = [
            "fileperframe",
            # Lock some Avalon attributes
            "family",
            "id",
        ]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
