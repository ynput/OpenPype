import hou
from openpype.hosts.houdini.api import plugin


class CreateUSDRender(plugin.Creator):
    """USD Render ROP in /stage"""

    label = "USD Render (experimental)"
    family = "usdrender"
    icon = "magic"

    def __init__(self, *args, **kwargs):
        super(CreateUSDRender, self).__init__(*args, **kwargs)

        self.parent = hou.node("/stage")

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "usdrender"})

    def _process(self, instance):
        """Creator main entry point.

        Args:
            instance (hou.Node): Created Houdini instance.

         """
        parms = {
            # Render frame range
            "trange": 1
        }
        if self.nodes:
            node = self.nodes[0]
            parms.update({"loppath": node.path()})
        instance.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
