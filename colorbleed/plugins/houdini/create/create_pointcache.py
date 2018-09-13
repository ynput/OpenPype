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

        # create an ordered dict with the existing data first
        data = OrderedDict(**self.data)

        # Set node type to create for output
        data["node_type"] = "alembic"

        self.data = data

    def process(self):
        instance = super(CreatePointCache, self).process()

        parms = {"build_from_path": 1,
                 "path_attrib": "path",
                 "use_sop_path": True,
                 "filename": "$HIP/%s.abc" % self.name}

        if self.nodes:
            node = self.nodes[0]
            parms.update({"sop_path": "%s/OUT" % node.path()})

        instance.setParms(parms)
