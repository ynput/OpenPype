from openpype.hosts.houdini.api import plugin
from openpype.lib import EnumDef

class CreateArnoldRop(plugin.HoudiniCreator):
    """Arnold ROP"""

    identifier = "io.openpype.creators.houdini.arnold_rop"
    label = "Arnold ROP"
    family = "arnold_rop"
    icon = "magic"
    defaults = ["master"]

    # Default extension
    ext = ".exr"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou

        # Remove the active, we are checking the bypass flag of the nodes
        instance_data.pop("active", None)
        instance_data.update({"node_type": "arnold"})

        # Add chunk size attribute
        instance_data["chunkSize"] = 1

        instance = super(CreateArnoldRop, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: plugin.CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))

        # Hide Properties Tab on Arnold ROP since that's used
        # for rendering instead of .ass Archive Export
        parm_template_group = instance_node.parmTemplateGroup()
        parm_template_group.hideFolder("Properties", True)
        instance_node.setParmTemplateGroup(parm_template_group)

        ext = pre_create_data.get("image_format")

        filepath = "{}{}".format(
            hou.text.expandString("$HIP/pyblish/"),
            "{}.$F4{}".format(subset_name, ext)
        )
        parms = {
            # Render frame range
            "trange": 1,

            # Arnold ROP settings
            "ar_picture": filepath,
            "ar_exr_half_precision": 1           # half precision
        }

        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateArnoldRop, self).get_pre_create_attr_defs()

        image_format_enum = [
            "bmp", "cin", "exr", "jpg", "pic", "pic.gz", "png",
            "rad", "rat", "rta", "sgi", "tga", "tif",
        ]

        return attrs + [
            EnumDef("image_format",
                    image_format_enum,
                    default=self.ext,
                    label="Image Format Options")
        ]
