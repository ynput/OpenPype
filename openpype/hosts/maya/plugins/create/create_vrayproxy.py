from openpype.hosts.maya.api import plugin


class CreateVrayProxy(plugin.Creator):
    """Alembic pointcache for animated data"""

    name = "vrayproxy"
    label = "VRay Proxy"
    family = "vrayproxy"
    icon = "gears"

    vrmesh = True
    alembic = True

    def __init__(self, *args, **kwargs):
        super(CreateVrayProxy, self).__init__(*args, **kwargs)

        self.data["animation"] = False
        self.data["frameStart"] = 1
        self.data["frameEnd"] = 1

        # Write vertex colors
        self.data["vertexColors"] = False

        self.data["vrmesh"] = self.vrmesh
        self.data["alembic"] = self.alembic
