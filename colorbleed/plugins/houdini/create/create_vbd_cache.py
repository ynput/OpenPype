from collections import OrderedDict

from avalon import houdini


class CreateVDBCache(houdini.Creator):
    """Alembic pointcache for animated data"""

    name = "vbdcache"
    label = "VDB Cache"
    family = "colorbleed.vbdcache"
    icon = "cloud"

    def __init__(self, *args, **kwargs):
        super(CreateVDBCache, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first
        data = OrderedDict(**self.data)

        # Set node type to create for output
        data["node_type"] = "geometry"

        self.data = data

    def process(self):
        instance = super(CreateVDBCache, self).process()

        parms = {}
        if self.nodes:
            parms.update({"soppath": self.nodes[0].path()})

        instance.setParms()
