from collections import OrderedDict

import avalon.maya


class CreateVrayProxy(avalon.maya.Creator):
    """Alembic pointcache for animated data"""

    name = "vrayproxy"
    label = "VRay Proxy"
    family = "studio.vrayproxy"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreateVrayProxy, self).__init__(*args, **kwargs)

        data = OrderedDict(**self.data)

        data["animation"] = False
        data["startFrame"] = 1
        data["endFrame"] = 1

        self.data.update(data)
