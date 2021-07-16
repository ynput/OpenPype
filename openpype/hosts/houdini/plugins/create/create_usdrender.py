import hou
from openpype.hosts.houdini.api import plugin


class CreateUSDRender(plugin.Creator):
    """USD Render ROP in /stage"""

    label = "USD Render"
    family = "usdrender"
    icon = "magic"

    def __init__(self, *args, **kwargs):
        super(CreateUSDRender, self).__init__(*args, **kwargs)

        self.parent = hou.node("/stage")

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "usdrender_rop"})

    def process(self):
        instance = super(CreateUSDRender, self).process()

        parms = {
            # Render frame range
            "trange": 1
        }
        instance.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
