from avalon import houdini


class CreateVDBCache(houdini.Creator):
    """Alembic pointcache for animated data"""

    name = "vbdcache"
    label = "VDB Cache"
    family = "vdbcache"
    icon = "cloud"

    def __init__(self, *args, **kwargs):
        super(CreateVDBCache, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({
            "node_type": "geometry",  # Set node type to create for output
            "executeBackground": True  # Render node in background
        })

    def process(self):
        instance = super(CreateVDBCache, self).process()

        parms = {"sopoutput": "$HIP/pyblish/%s.$F4.vdb" % self.name,
                 "initsim": True}

        if self.nodes:
            node = self.nodes[0]
            parms.update({"sop_path": node.path()})

        instance.setParms(parms)
