from collections import OrderedDict

from avalon import houdini


class CreateAlembicCamera(houdini.Creator):

    name = "camera"
    label = "Camera (Abc)"
    family = "colorbleed.camera"
    icon = "camera"

    def __init__(self, *args, **kwargs):
        super(CreateAlembicCamera, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first
        data = OrderedDict(**self.data)

        # Set node type to create for output
        data["node_type"] = "alembic"

        self.data = data

    def process(self):
        instance = super(CreateAlembicCamera, self).process()

        parms = {"use_sop_path": True,
                 "build_from_path": True,
                 "path_attrib": "path",
                 "filename": "$HIP/pyblish/%s.abc" % self.name}

        if self.nodes:
            node = self.nodes[0]
            parms.update({"sop_path": node.path()})

        instance.setParms(parms)
