# -*- coding: utf-8 -*-
"""Creator plugin for creating Redshift proxies."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance


class CreateRedshiftProxy(plugin.HoudiniCreator):
    """Redshift Proxy"""
    identifier = "io.openpype.creators.houdini.redshiftproxy"
    label = "Redshift Proxy"
    family = "redshiftproxy"
    icon = "magic"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou  # noqa
        # Remove the active, we are checking the bypass flag of the nodes
        instance_data.pop("active", None)

        # Redshift provides a `Redshift_Proxy_Output` node type which shows
        # a limited set of parameters by default and is set to extract a
        # Redshift Proxy. However when "imprinting" extra parameters needed
        # for OpenPype it starts showing all its parameters again. It's unclear
        # why this happens.
        # TODO: Somehow enforce so that it only shows the original limited
        #       attributes of the Redshift_Proxy_Output node type
        instance_data.update({"node_type": "Redshift_Proxy_Output"})

        instance = super(CreateRedshiftProxy, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))
        file_path = "{}/pyblish/`chs('subset')`.$F4.rs".format(
            hou.text.expandString("$HIP")
        )
        parms = {
            "RS_archive_file": file_path,
        }

        if self.selected_nodes:
            parms["RS_archive_sopPath"] = self.selected_nodes[0].path()

        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id", "prim_to_detail_pattern"]
        self.lock_parameters(instance_node, to_lock)
