from openpype.hosts.houdini.api import plugin
from openpype.pipeline import (
    CreatedInstance,
    OpenPypePyblishPluginMixin
)


class CreateReview(plugin.HoudiniCreator, OpenPypePyblishPluginMixin):
    """Review with OpenGL ROP"""

    identifier = "io.openpype.creators.houdini.review"
    label = "Review"
    family = "review"
    icon = "video-camera"

    # Default settings for the ROP
    # todo: expose in OpenPype settings?
    override_resolution = True
    width = 1280
    height = 720
    aspect = 1.0

    def create(self, subset_name, instance_data, pre_create_data):

        import hou

        # Remove the active, we are checking the bypass flag of the nodes
        instance_data.pop("active", None)

        instance_data["node_type"] = "opengl"

        instance = super(CreateReview, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))

        frame_range = hou.playbar.frameRange()

        parms = {
            "picture": '$HIP/pyblish/`chs("subset")`/`chs("subset")`.$F4.png',
            # Render frame range
            "trange": 1,

            # Unlike many other ROP nodes the opengl node does not default
            # to expression of $FSTART and $FEND so we preserve that behavior
            # but do set the range to the frame range of the playbar
            "f1": frame_range[0],
            "f2": frame_range[1],
        }

        if self.override_resolution:
            # Override resolution
            parms.update({
                "tres": True,   # Override Camera Resolution
                "res1": self.width,
                "res2": self.height,
                "aspect": self.aspect
            })

        if self.selected_nodes:
            # todo: allow only object paths?
            node_paths = " ".join(node.path() for node in self.selected_nodes)
            parms.update({"scenepath": node_paths})

        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = [
            "family",
            "id"
        ]
        self.lock_parameters(instance_node, to_lock)
