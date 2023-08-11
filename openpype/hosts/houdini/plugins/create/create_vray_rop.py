# -*- coding: utf-8 -*-
"""Creator plugin to create VRay ROP."""
import hou

from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance
from openpype.lib import EnumDef, BoolDef


class CreateVrayROP(plugin.HoudiniCreator):
    """VRay ROP"""

    identifier = "io.openpype.creators.houdini.vray_rop"
    label = "VRay ROP"
    family = "vray_rop"
    icon = "magic"
    ext = "exr"

    # Default to split export and render jobs
    export_job = True

    def create(self, subset_name, instance_data, pre_create_data):

        instance_data.pop("active", None)
        instance_data.update({"node_type": "vray_renderer"})
        # Add chunk size attribute
        instance_data["chunkSize"] = 10
        # Submit for job publishing
        instance_data["farm"] = pre_create_data.get("farm")

        instance = super(CreateVrayROP, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))

        # Add IPR for Vray
        basename = instance_node.name()
        try:
            ipr_rop = instance_node.parent().createNode(
                "vray", node_name=basename + "_IPR"
            )
        except hou.OperationFailed:
            raise plugin.OpenPypeCreatorError(
                "Cannot create Vray render node. "
                "Make sure Vray installed and enabled!"
            )

        ipr_rop.setPosition(instance_node.position() + hou.Vector2(0, -1))
        ipr_rop.parm("rop").set(instance_node.path())

        parms = {
            "trange": 1,
            "SettingsEXR_bits_per_channel": "16"   # half precision
        }

        if pre_create_data.get("export_job"):
            scene_filepath = \
                "{export_dir}{subset_name}/{subset_name}.$F4.vrscene".format(
                    export_dir=hou.text.expandString("$HIP/pyblish/vrscene/"),
                    subset_name=subset_name,
                )
            # Setting render_export_mode to "2" because that's for
            # "Export only" ("1" is for "Export & Render")
            parms["render_export_mode"] = "2"
            parms["render_export_filepath"] = scene_filepath

        if self.selected_nodes:
            # set up the render camera from the selected node
            camera = None
            for node in self.selected_nodes:
                if node.type().name() == "cam":
                    camera = node.path()
            parms.update({
                "render_camera": camera or ""
            })

        # Enable render element
        ext = pre_create_data.get("image_format")
        instance_data["RenderElement"] = pre_create_data.get("render_element_enabled")         # noqa
        if pre_create_data.get("render_element_enabled", True):
            # Vray has its own tag for AOV file output
            filepath = "{renders_dir}{subset_name}/{subset_name}.{fmt}".format(
                renders_dir=hou.text.expandString("$HIP/pyblish/renders/"),
                subset_name=subset_name,
                fmt="${aov}.$F4.{ext}".format(aov="AOV",
                                              ext=ext)
            )
            filepath = "{}{}".format(
                hou.text.expandString("$HIP/pyblish/renders/"),
                "{}/{}.${}.$F4.{}".format(subset_name,
                                          subset_name,
                                          "AOV",
                                          ext)
            )
            re_rop = instance_node.parent().createNode(
                "vray_render_channels",
                node_name=basename + "_render_element"
            )
            # move the render element node next to the vray renderer node
            re_rop.setPosition(instance_node.position() + hou.Vector2(0, 1))
            re_path = re_rop.path()
            parms.update({
                "use_render_channels": 1,
                "SettingsOutput_img_file_path": filepath,
                "render_network_render_channels": re_path
            })

        else:
            filepath = "{renders_dir}{subset_name}/{subset_name}.{fmt}".format(
                renders_dir=hou.text.expandString("$HIP/pyblish/renders/"),
                subset_name=subset_name,
                fmt="$F4.{ext}".format(ext=ext)
            )
            parms.update({
                "use_render_channels": 0,
                "SettingsOutput_img_file_path": filepath
            })

        custom_res = pre_create_data.get("override_resolution")
        if custom_res:
            parms.update({"override_camerares": 1})

        instance_node.setParms(parms)

        # lock parameters from AVALON
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)

    def remove_instances(self, instances):
        for instance in instances:
            node = instance.data.get("instance_node")
            # for the extra render node from the plugins
            # such as vray and redshift
            ipr_node = hou.node("{}{}".format(node, "_IPR"))
            if ipr_node:
                ipr_node.destroy()
            re_node = hou.node("{}{}".format(node,
                                             "_render_element"))
            if re_node:
                re_node.destroy()

        return super(CreateVrayROP, self).remove_instances(instances)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateVrayROP, self).get_pre_create_attr_defs()
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
                    default=self.ext,
                    label="Image Format Options"),
            BoolDef("override_resolution",
                    label="Override Camera Resolution",
                    tooltip="Override the current camera "
                            "resolution, recommended for IPR.",
                    default=False),
            BoolDef("render_element_enabled",
                    label="Render Element",
                    tooltip="Create Render Element Node "
                            "if enabled",
                    default=False)
        ]
