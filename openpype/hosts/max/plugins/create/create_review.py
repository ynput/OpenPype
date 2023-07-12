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
        instance_data["rndLevel"] = pre_create_data.get("rndLevel")

        super(CreateReview, self).create(
            subset_name,
            instance_data,
            pre_create_data)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateReview, self).get_pre_create_attr_defs()

        image_format_enum = [
            "bmp", "cin", "exr", "jpg", "hdr", "rgb", "png",
            "rla", "rpf", "dds", "sgi", "tga", "tif", "vrimg"
        ]

        rndLevel_enum = [
            "smoothhighlights", "smooth", "facethighlights",
            "facet", "flat", "litwireframe", "wireframe", "box"
        ]

        return attrs + [
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
            EnumDef("rndLevel",
                    rndLevel_enum,
                    default="smoothhighlights",
                    label="Preference")
        ]
