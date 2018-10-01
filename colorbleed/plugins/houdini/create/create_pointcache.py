from collections import OrderedDict

from avalon import houdini


class CreatePointCache(houdini.Creator):
    """Alembic pointcache for animated data"""

    name = "pointcache"
    label = "Point Cache"
    family = "colorbleed.pointcache"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "alembic"})

    def process(self):
        instance = super(CreatePointCache, self).process()

        parms = {"use_sop_path": True,
                 "build_from_path": True,
                 "path_attrib": "path",
                 "filename": "$HIP/pyblish/%s.abc" % self.name}

        if self.nodes:
            node = self.nodes[0]
            parms.update({"sop_path": "%s/OUT" % node.path()})

        instance.setParms(parms)
