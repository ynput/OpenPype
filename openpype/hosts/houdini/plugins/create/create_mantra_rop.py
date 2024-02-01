# -*- coding: utf-8 -*-
"""Creator plugin to create Mantra ROP."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance
from openpype.lib import EnumDef, BoolDef


class CreateMantraROP(plugin.HoudiniCreator):
    """Mantra ROP"""
    identifier = "io.openpype.creators.houdini.mantra_rop"
    label = "Mantra ROP"
    family = "mantra_rop"
    icon = "magic"

    # Default to split export and render jobs
    export_job = True

    def create(self, subset_name, instance_data, pre_create_data):
        import hou  # noqa

        instance_data.pop("active", None)
        instance_data.update({"node_type": "ifd"})
        # Add chunk size attribute
        instance_data["chunkSize"] = 10
        # Submit for job publishing
        instance_data["farm"] = pre_create_data.get("farm")

        instance = super(CreateMantraROP, self).create(
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
            # Mantra ROP Setting
            "vm_picture": filepath,
        }

        if pre_create_data.get("export_job"):
            ifd_filepath = \
                "{export_dir}{subset_name}/{subset_name}.$F4.ifd".format(
                    export_dir=hou.text.expandString("$HIP/pyblish/ifd/"),
                    subset_name=subset_name,
                )
            parms["soho_outputmode"] = 1
            parms["soho_diskfile"] = ifd_filepath

        if self.selected_nodes:
            # If camera found in selection
            # we will use as render camera
            camera = None
            for node in self.selected_nodes:
                if node.type().name() == "cam":
                    camera = node.path()

            if not camera:
                self.log.warning("No render camera found in selection")

            parms.update({"camera": camera or ""})

        custom_res = pre_create_data.get("override_resolution")
        if custom_res:
            parms.update({"override_camerares": 1})
        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateMantraROP, self).get_pre_create_attr_defs()

        image_format_enum = [
            "bmp", "cin", "exr", "jpg", "pic", "pic.gz", "png",
            "rad", "rat", "rta", "sgi", "tga", "tif",
        ]

        return attrs + [
            BoolDef("farm",
                    label="Submitting to Farm",
                    default=True),
            BoolDef("export_job",
                    label="Split export and render jobs",
                    default=self.export_job),
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
