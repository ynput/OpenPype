import pyblish.api


class CollectOutputSOPPath(pyblish.api.InstancePlugin):
    """Collect the out node's SOP/COP Path value."""

    order = pyblish.api.CollectorOrder
    families = [
        "pointcache",
        "camera",
        "vdbcache",
        "imagesequence",
        "usd",
        "usdrender",
        "redshiftproxy"
    ]

    hosts = ["houdini"]
    label = "Collect Output Node Path"

    def process(self, instance):

        import hou

        node = instance[0]

        # Get sop path
        node_type = node.type().name()
        if node_type == "geometry":
            out_node = node.parm("soppath").evalAsNode()

        elif node_type == "alembic":

            # Alembic can switch between using SOP Path or object
            if node.parm("use_sop_path").eval():
                out_node = node.parm("sop_path").evalAsNode()
            else:
                root = node.parm("root").eval()
                objects = node.parm("objects").eval()
                path = root + "/" + objects
                out_node = hou.node(path)

        elif node_type == "comp":
            out_node = node.parm("coppath").evalAsNode()

        elif node_type == "usd" or node_type == "usdrender":
            out_node = node.parm("loppath").evalAsNode()

        elif node_type == "usd_rop" or node_type == "usdrender_rop":
            # Inside Solaris e.g. /stage (not in ROP context)
            # When incoming connection is present it takes it directly
            inputs = node.inputs()
            if inputs:
                out_node = inputs[0]
            else:
                out_node = node.parm("loppath").evalAsNode()

        elif node_type == "Redshift_Proxy_Output":
            out_node = node.parm("RS_archive_sopPath").evalAsNode()
        else:
            raise ValueError(
                "ROP node type '%s' is" " not supported." % node_type
            )

        if not out_node:
            self.log.warning("No output node collected.")
            return

        self.log.debug("Output node: %s" % out_node.path())
        instance.data["output_node"] = out_node
