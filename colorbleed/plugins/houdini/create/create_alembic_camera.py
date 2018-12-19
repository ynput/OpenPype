from avalon import houdini


class CreateAlembicCamera(houdini.Creator):

    name = "camera"
    label = "Camera (Abc)"
    family = "colorbleed.camera"
    icon = "camera"

    def __init__(self, *args, **kwargs):
        super(CreateAlembicCamera, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        # Set node type to create for output
        self.data.update({"node_type": "alembic"})

    def process(self):
        instance = super(CreateAlembicCamera, self).process()

        parms = {"use_sop_path": True,
                 "filename": "$HIP/pyblish/%s.abc" % self.name}

        if self.nodes:
            node = self.nodes[0]
            parms.update({"sop_path": node.path()})

        instance.setParms(parms)
