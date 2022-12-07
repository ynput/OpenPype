from openpype.hosts.houdini.api import plugin


class CreateArnoldRop(plugin.Creator):
    """Arnold ROP"""

    label = "Arnold ROP"
    family = "arnold_rop"
    icon = "magic"
    defaults = ["master"]

    def __init__(self, *args, **kwargs):
        super(CreateArnoldRop, self).__init__(*args, **kwargs)

        # Clear the family prefix from the subset
        subset = self.data["subset"]
        subset_no_prefix = subset[len(self.family):]
        subset_no_prefix = subset_no_prefix[0].lower() + subset_no_prefix[1:]
        self.data["subset"] = subset_no_prefix

        # Add chunk size attribute
        self.data["chunkSize"] = 1

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "arnold"})

    def _process(self, instance):

        basename = instance.name()
        instance.setName(basename + "_ROP", unique_name=True)

        prefix = '${HIP}/render/${HIPNAME}/`chs("subset")`.$F4.exr'
        parms = {
            # Render frame range
            "trange": 1,

            # Arnold ROP settings
            "ar_picture": prefix,
            "ar_exr_half_precision": 1           # half precision
        }
        instance.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
