import hou
from openpype.hosts.houdini.api import plugin


class CreateRedshiftROP(plugin.Creator):
    """Redshift ROP"""

    label = "Redshift ROP"
    family = "redshift_rop"
    icon = "magic"
    defaults = ["master"]

    def __init__(self, *args, **kwargs):
        super(CreateRedshiftROP, self).__init__(*args, **kwargs)

        # Clear the family prefix from the subset
        subset = self.data["subset"]
        subset_no_prefix = subset[len(self.family):]
        subset_no_prefix = subset_no_prefix[0].lower() + subset_no_prefix[1:]
        self.data["subset"] = subset_no_prefix

        # Add chunk size attribute
        self.data["chunkSize"] = 10

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "Redshift_ROP"})

    def _process(self, instance):
        """Creator main entry point.

        Args:
            instance (hou.Node): Created Houdini instance.

        """
        basename = instance.name()
        instance.setName(basename + "_ROP", unique_name=True)

        # Also create the linked Redshift IPR Rop
        try:
            ipr_rop = self.parent.createNode(
                "Redshift_IPR", node_name=basename + "_IPR"
            )
        except hou.OperationFailed:
            raise Exception(("Cannot create Redshift node. Is Redshift "
                             "installed and enabled?"))

        # Move it to directly under the Redshift ROP
        ipr_rop.setPosition(instance.position() + hou.Vector2(0, -1))

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
        instance.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
