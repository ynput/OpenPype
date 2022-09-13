from openpype.hosts.houdini.api import plugin


class CreateReview(plugin.Creator):
    """Review with OpenGL ROP"""

    label = "Review"
    family = "review"
    icon = "video-camera"

    def __init__(self, *args, **kwargs):
        super(CreateReview, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "opengl"})

    def _process(self, instance):
        """Creator main entry point.

        Args:
            instance (hou.Node): Created Houdini instance.

        """
        import hou

        frame_range = hou.playbar.frameRange()

        parms = {
            "picture": "$HIP/pyblish/{0}/{0}.$F4.png".format(self.name),
            # Render frame range
            "trange": 1,

            # Unlike many other ROP nodes the opengl node does not default
            # to expression of $FSTART and $FEND so we preserve that behavior
            # but do set the range to the frame range of the playbar
            "f1": frame_range[0],
            "f2": frame_range[1]
        }

        if self.nodes:
            # todo: allow only object paths?
            node_paths = " ".join(node.path() for node in self.nodes)
            parms.update({"scenepath": node_paths})

        instance.setParms(parms)

        # Lock any parameters in this list
        to_lock = [
            # Lock some Avalon attributes
            "family",
            "id",
        ]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
