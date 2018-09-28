from avalon import houdini


class CreateVDBCache(houdini.Creator):
    """Alembic pointcache for animated data"""

    name = "vbdcache"
    label = "VDB Cache"
    family = "colorbleed.vdbcache"
    icon = "cloud"

    def __init__(self, *args, **kwargs):
        super(CreateVDBCache, self).__init__(*args, **kwargs)

        self.data.update({
            "node_type": "geometry",  # Set node type to create for output
            "executeBackground": True  # Render node in background
        })

    def process(self):
        instance = super(CreateVDBCache, self).process()

        parms = {"sopoutput": "$HIP/pyblish/%s.$F4.vdb" % self.name}
        if self.nodes:
            parms.update({"soppath": self.nodes[0].path()})

        instance.setParms(parms)
