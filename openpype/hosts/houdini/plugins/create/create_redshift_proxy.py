import hou
from openpype.hosts.houdini.api import plugin


class CreateRedshiftProxy(plugin.Creator):
    """Redshift Proxy"""

    label = "Redshift Proxy"
    family = "redshiftproxy"
    icon = "magic"

    def __init__(self, *args, **kwargs):
        super(CreateRedshiftProxy, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        # Redshift provides a `Redshift_Proxy_Output` node type which shows
        # a limited set of parameters by default and is set to extract a
        # Redshift Proxy. However when "imprinting" extra parameters needed
        # for OpenPype it starts showing all its parameters again. It's unclear
        # why this happens.
        # TODO: Somehow enforce so that it only shows the original limited
        #       attributes of the Redshift_Proxy_Output node type
        self.data.update({"node_type": "Redshift_Proxy_Output"})

    def _process(self, instance):
        """Creator main entry point.

        Args:
            instance (hou.Node): Created Houdini instance.

        """
        parms = {
            "RS_archive_file": '$HIP/pyblish/`chs("subset")`.$F4.rs',
        }

        if self.nodes:
            node = self.nodes[0]
            path = node.path()
            parms["RS_archive_sopPath"] = path

        instance.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
