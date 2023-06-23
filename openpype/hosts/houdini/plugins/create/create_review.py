# -*- coding: utf-8 -*-
"""Creator plugin for creating openGL reviews."""
from openpype.hosts.houdini.api import plugin
from openpype.lib import EnumDef, BoolDef, NumberDef


class CreateReview(plugin.HoudiniCreator):
    """Review with OpenGL ROP"""

    identifier = "io.openpype.creators.houdini.review"
    label = "Review"
    family = "review"
    icon = "video-camera"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou

        instance_data.pop("active", None)
        instance_data.update({"node_type": "opengl"})
        instance_data["imageFormat"] = pre_create_data.get("imageFormat")
        instance_data["keepImages"] = pre_create_data.get("keepImages")
        instance_data["sources"] = pre_create_data.get("sources")

        instance = super(CreateReview, self).create(
            subset_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))

        frame_range = hou.playbar.frameRange()

        filepath = "{root}/{subset}/{subset}.$F4.{ext}".format(
            root=hou.text.expandString("$HIP/pyblish"),
            subset="`chs(\"subset\")`",  # keep dynamic link to subset
            ext=pre_create_data.get("image_format") or "png"
        )

        parms = {
            "picture": filepath,

            "trange": 1,

            # Unlike many other ROP nodes the opengl node does not default
            # to expression of $FSTART and $FEND so we preserve that behavior
            # but do set the range to the frame range of the playbar
            "f1": frame_range[0],
            "f2": frame_range[1],
        }

        override_resolution = pre_create_data.get("override_resolution")
        if override_resolution:
            parms.update({
                "tres": override_resolution,
                "res1": pre_create_data.get("resx"),
                "res2": pre_create_data.get("resy"),
                "aspect": pre_create_data.get("aspect"),
            })

        sources = pre_create_data.get("sources")

        if self.selected_nodes:
            # The first camera found in selection we will use as camera
            # Other node types we set in force objects
            camera = None
            lop_network = None
            force_objects = []
            for node in self.selected_nodes:
                path = node.path()
                if node.type().name() == "cam":
                    if camera:
                        continue
                    camera = path
                elif node.type().name() == "lopnet":
                    if lop_network:
                        continue
                    lop_network = path
                else:
                    force_objects.append(path)

            if not camera:
                self.log.warning("No camera found in selection.")


            if sources == 0:
                parms.update({
                    "opsource": sources,
                    "camera": camera or "",
                    "scenepath": "/obj",
                    "forceobjects": " ".join(force_objects),
                    "vobjects": ""  # clear candidate objects from '*' value
                })
            else:
                if not lop_network:
                    self.log.warning("No LOP network found in selection.")
                parms.update({
                    "opsource": sources,
                    "cameraprim": camera or "",
                    "loppath": lop_network
                })

        instance_node.setParms(parms)

        to_lock = ["id", "family"]

        self.lock_parameters(instance_node, to_lock)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateReview, self).get_pre_create_attr_defs()

        image_format_enum = [
            "bmp", "cin", "exr", "jpg", "pic", "pic.gz", "png",
            "rad", "rat", "rta", "sgi", "tga", "tif",
        ]


        return attrs + [
            BoolDef("keepImages",
                    label="Keep Image Sequences",
                    default=False),
            EnumDef("sources",
                    items={
                        0: "Objects",
                        1: "LOPs"
                    },
                    default=0,
                    label="Source"),
            EnumDef("imageFormat",
                    image_format_enum,
                    default="png",
                    label="Image Format Options"),
            BoolDef("override_resolution",
                    label="Override resolution",
                    tooltip="When disabled the resolution set on the camera "
                            "is used instead.",
                    default=True),
            NumberDef("resx",
                      label="Resolution Width",
                      default=1280,
                      minimum=2,
                      decimals=0),
            NumberDef("resy",
                      label="Resolution Height",
                      default=720,
                      minimum=2,
                      decimals=0),
            NumberDef("aspect",
                      label="Aspect Ratio",
                      default=1.0,
                      minimum=0.0001,
                      decimals=3)
        ]
