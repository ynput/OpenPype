# -*- coding: utf-8 -*-
"""Creator plugin to create Redshift ROP."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance


class CreateRedshiftROP(plugin.HoudiniCreator):
    """Redshift ROP"""
    identifier = "io.openpype.creators.houdini.redshift_rop"
    label = "Redshift ROP"
    family = "redshift_rop"
    icon = "magic"
    defaults = ["master"]

    def create(self, subset_name, instance_data, pre_create_data):
        import hou  # noqa

        instance_data.pop("active", None)
        instance_data.update({"node_type": "Redshift_ROP"})
        # Add chunk size attribute
        instance_data["chunkSize"] = 10

        # Clear the family prefix from the subset
        subset = subset_name
        subset_no_prefix = subset[len(self.family):]
        subset_no_prefix = subset_no_prefix[0].lower() + subset_no_prefix[1:]
        subset_name = subset_no_prefix

        instance = super(CreateRedshiftROP, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))

        basename = instance_node.name()
        instance_node.setName(basename + "_ROP", unique_name=True)

        # Also create the linked Redshift IPR Rop
        try:
            ipr_rop = self.parent.createNode(
                "Redshift_IPR", node_name=basename + "_IPR"
            )
        except hou.OperationFailed:
            raise plugin.OpenPypeCreatorError(
                ("Cannot create Redshift node. Is Redshift "
                 "installed and enabled?"))

        # Move it to directly under the Redshift ROP
        ipr_rop.setPosition(instance_node.position() + hou.Vector2(0, -1))

        # Set the linked rop to the Redshift ROP
        ipr_rop.parm("linked_rop").set(ipr_rop.relativePathTo(instance))

        prefix = '${HIP}/render/${HIPNAME}/`chs("subset")`.${AOV}.$F4.exr'
        parms = {
            # Render frame range
            "trange": 1,
            # Redshift ROP settings
            "RS_outputFileNamePrefix": prefix,
            "RS_outputMultilayerMode": 0,  # no multi-layered exr
            "RS_outputBeautyAOVSuffix": "beauty",
        }
        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)
