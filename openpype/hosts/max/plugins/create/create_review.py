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

    review_width = 1920
    review_height = 1080
    percentSize = 100
    keep_images = False
    image_format = "png"
    visual_style = "Realistic"
    viewport_preset = "Quality"
    vp_texture = True
    anti_aliasing = "None"

    def apply_settings(self, project_settings):
        settings = project_settings["max"]["CreateReview"]  # noqa

        # Take some defaults from settings
        self.review_width = settings.get("review_width", self.review_width)
        self.review_height = settings.get("review_height", self.review_height)
        self.percentSize = settings.get("percentSize", self.percentSize)
        self.keep_images = settings.get("keep_images", self.keep_images)
        self.image_format = settings.get("image_format", self.image_format)
        self.visual_style = settings.get("visual_style", self.visual_style)
        self.viewport_preset = settings.get(
            "viewport_preset", self.viewport_preset)
        self.anti_aliasing = settings.get(
            "anti_aliasing", self.anti_aliasing)
        self.vp_texture = settings.get("vp_texture", self.vp_texture)

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
                    "antialiasingQuality",
                    "vpTexture"]:
            if key in pre_create_data:
                creator_attributes[key] = pre_create_data[key]

        super(CreateReview, self).create(
            subset_name,
            instance_data,
            pre_create_data)

    def get_instance_attr_defs(self):
        image_format_enum = ["exr", "jpg", "png", "tga"]

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
        anti_aliasing_enum = ["None", "2X", "4X", "8X"]

        return [
            NumberDef("review_width",
                      label="Review width",
                      decimals=0,
                      minimum=0,
                      default=self.review_width),
            NumberDef("review_height",
                      label="Review height",
                      decimals=0,
                      minimum=0,
                      default=self.review_height),
            NumberDef("percentSize",
                      label="Percent of Output",
                      default=self.percentSize,
                      minimum=1,
                      decimals=0),
            BoolDef("keepImages",
                    label="Keep Image Sequences",
                    default=self.keep_images),
            EnumDef("imageFormat",
                    image_format_enum,
                    default=self.image_format,
                    label="Image Format Options"),
            EnumDef("visualStyleMode",
                    visual_style_preset_enum,
                    default=self.visual_style,
                    label="Preference"),
            EnumDef("viewportPreset",
                    preview_preset_enum,
                    default=self.viewport_preset,
                    label="Preview Preset"),
            EnumDef("antialiasingQuality",
                    anti_aliasing_enum,
                    default=self.anti_aliasing,
                    label="Anti-aliasing Quality"),
            BoolDef("vpTexture",
                    label="Viewport Texture",
                    default=self.vp_texture)
        ]

    def get_pre_create_attr_defs(self):
        # Use same attributes as for instance attributes
        attrs = super().get_pre_create_attr_defs()
        return attrs + self.get_instance_attr_defs()
