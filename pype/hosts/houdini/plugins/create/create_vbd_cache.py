from pype.hosts.houdini.api import plugin


class CreateVDBCache(plugin.Creator):
    """OpenVDB from Geometry ROP"""

    name = "vbdcache"
    label = "VDB Cache"
    family = "vdbcache"
    icon = "cloud"

    def __init__(self, *args, **kwargs):
        super(CreateVDBCache, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        # Set node type to create for output
        self.data["node_type"] = "geometry"

    def process(self):
        instance = super(CreateVDBCache, self).process()

        parms = {"sopoutput": "$HIP/pyblish/%s.$F4.vdb" % self.name,
                 "initsim": True}

        if self.nodes:
            node = self.nodes[0]
            parms.update({"soppath": node.path()})

        instance.setParms(parms)
