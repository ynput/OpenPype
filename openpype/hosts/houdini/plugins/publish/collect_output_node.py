import pyblish.api


class CollectOutputSOPPath(pyblish.api.InstancePlugin):
    """Collect the out node's SOP Path value."""

    order = pyblish.api.CollectorOrder
    families = ["pointcache",
                "vdbcache"]
    hosts = ["houdini"]
    label = "Collect Output SOP Path"

    def process(self, instance):

        import hou

        node = instance[0]

        # Get sop path
        if node.type().name() == "alembic":
            sop_path_parm = "sop_path"
        else:
            sop_path_parm = "soppath"

        sop_path = node.parm(sop_path_parm).eval()
        out_node = hou.node(sop_path)

        instance.data["output_node"] = out_node
