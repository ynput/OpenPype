from collections import OrderedDict

from avalon import houdini


class CreateVDBCache(houdini.Creator):
    """Alembic pointcache for animated data"""

    name = "vbdcache"
    label = "VDB Cache"
    family = "colorbleed.vdbcache"
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

        parms = {"sopoutput": "$HIP/geo/%s.$F4.vdb" % self.name}
        if self.nodes:
            parms.update({"soppath": self.nodes[0].path()})

        instance.setParms(parms)
