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
        # Transfer settings from pre create to instance
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        for key in ["imageFormat",
                    "keepImages",
                    "review_width",
                    "review_height",
                    "percentSize",
                    "visualStyleMode",
                    "viewportPreset",
                    "vpTexture"]:
            if key in pre_create_data:
                creator_attributes[key] = pre_create_data[key]

        super(CreateReview, self).create(
            subset_name,
            instance_data,
            pre_create_data)

    def get_instance_attr_defs(self):
        image_format_enum = ["exr", "jpg", "png"]

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
            NumberDef("review_width",
                      label="Review width",
                      decimals=0,
                      minimum=0,
                      default=1920),
            NumberDef("review_height",
                      label="Review height",
                      decimals=0,
                      minimum=0,
                      default=1080),
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
                    label="Pre-View Preset"),
            BoolDef("vpTexture",
                    label="Viewport Texture",
                    default=False)
        ]

    def get_pre_create_attr_defs(self):
        # Use same attributes as for instance attributes
        attrs = super().get_pre_create_attr_defs()
        return attrs + self.get_instance_attr_defs()
