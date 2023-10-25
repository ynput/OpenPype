# -*- coding: utf-8 -*-
"""Creator plugin to create Husk ROP."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance
from openpype.lib import EnumDef, BoolDef


class CreateHuskROP(plugin.HoudiniCreator):
    """Husk ROP"""
    identifier = "io.openpype.creators.houdini.husk_rop"
    label = "Husk ROP"
    family = "husk"
    icon = "magic"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou  # noqa

        instance_data.pop("active", None)
        instance_data.update({"node_type": "usdrender"})
        # Add chunk size attribute
        instance_data["chunkSize"] = 10
        # Submit for job publishing
        instance_data["farm"] = pre_create_data.get("farm")

        instance = super(CreateHuskROP, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))

        ext = pre_create_data.get("image_format")

        filepath = "{renders_dir}{subset_name}/{subset_name}.$F4.{ext}".format(
            renders_dir=hou.text.expandString("$HIP/pyblish/renders/"),
            subset_name=subset_name,
            ext=ext,
        )

        parms = {
            # Render Frame Range
            "trange": 1,
            # Husk ROP Setting
            "renderer": "HdVRayRendererPlugin",
            "outputimage": filepath,
        }

        # if self.selected_nodes:
        #     # If camera found in selection
        #     # we will use as render camera
        #     camera = None
        #     for node in self.selected_nodes:
        #         if node.type().name() == "cam":
        #             camera = node.path()

        #     if not camera:
        #         self.log.warning("No render camera found in selection")

        #     parms.update({"camera": camera or ""})

        # custom_res = pre_create_data.get("override_resolution")
        # if custom_res:
        #     parms.update({"override_camerares": 1})
        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "husk"]
        self.lock_parameters(instance_node, to_lock)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateHuskROP, self).get_pre_create_attr_defs()

        image_format_enum = [
            "bmp", "cin", "exr", "jpg", "pic", "pic.gz", "png",
            "rad", "rat", "rta", "sgi", "tga", "tif",
        ]

        return attrs + [
            BoolDef("farm",
                    label="Submitting to Farm",
                    default=True),
            EnumDef("image_format",
                    image_format_enum,
                    default="exr",
                    label="Image Format Options"),
            BoolDef("override_resolution",
                    label="Override Camera Resolution",
                    tooltip="Override the current camera "
                            "resolution, recommended for IPR.",
                    default=False)
        ]
