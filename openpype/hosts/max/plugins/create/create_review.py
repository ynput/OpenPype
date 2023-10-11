# -*- coding: utf-8 -*-
"""Creator plugin for creating review in Max."""
from openpype.hosts.max.api import plugin
from openpype.lib import BoolDef, EnumDef, NumberDef


class CreateReview(plugin.MaxCreator):
    """Review in 3dsMax"""

    identifier = "io.openpype.creators.max.review"
    label = "Review"
    family = "review"
    icon = "video-camera"

    def create(self, subset_name, instance_data, pre_create_data):

        instance_data["imageFormat"] = pre_create_data.get("imageFormat")
        instance_data["keepImages"] = pre_create_data.get("keepImages")
        instance_data["percentSize"] = pre_create_data.get("percentSize")
        instance_data["visualStyleMode"] = pre_create_data.get("visualStyleMode")
        # Transfer settings from pre create to instance
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        for key in ["imageFormat",
                    "keepImages",
                    "percentSize",
                    "visualStyleMode",
                    "viewportPreset"]:
            if key in pre_create_data:
                creator_attributes[key] = pre_create_data[key]

        super(CreateReview, self).create(
            subset_name,
            instance_data,
            pre_create_data)

    def get_instance_attr_defs(self):
        image_format_enum = [
            "bmp", "cin", "exr", "jpg", "hdr", "rgb", "png",
            "rla", "rpf", "dds", "sgi", "tga", "tif", "vrimg"
        ]

        visual_style_preset_enum = [
            "Realistic", "Shaded", "Facets",
            "ConsistentColors", "HiddenLine",
            "Wireframe", "BoundingBox", "Ink",
            "ColorInk", "Acrylic", "Tech", "Graphite",
            "ColorPencil", "Pastel", "Clay", "ModelAssist"
        ]
        preview_preset_enum = [
            "Quality", "Standard", "Performance",
            "DXMode", "Customize"]

        return [
            BoolDef("keepImages",
                    label="Keep Image Sequences",
                    default=False),
            EnumDef("imageFormat",
                    image_format_enum,
                    default="png",
                    label="Image Format Options"),
            NumberDef("percentSize",
                      label="Percent of Output",
                      default=100,
                      minimum=1,
                      decimals=0),
            EnumDef("visualStyleMode",
                    visual_style_preset_enum,
                    default="Realistic",
                    label="Preference"),
            EnumDef("viewportPreset",
                    preview_preset_enum,
                    default="Quality",
                    label="Pre-View Preset")
        ]

    def get_pre_create_attr_defs(self):
        # Use same attributes as for instance attributes
        return self.get_instance_attr_defs()
