from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.lib import (
    BoolDef,
    NumberDef,
    EnumDef
)

TRANSPARENCIES = [
    "preset",
    "simple",
    "object sorting",
    "weighted average",
    "depth peeling",
    "alpha cut"
]


class CreateReview(plugin.MayaCreator):
    """Playblast reviewable"""

    identifier = "io.openpype.creators.maya.review"
    label = "Review"
    family = "review"
    icon = "video-camera"

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs()

        defs.extend([
            NumberDef("review_width",
                      label="Review width",
                      tooltip="A value of zero will use the asset resolution.",
                      decimals=0,
                      minimum=0,
                      default=0),
            NumberDef("review_height",
                      label="Review height",
                      tooltip="A value of zero will use the asset resolution.",
                      decimals=0,
                      minimum=0,
                      default=0),
            BoolDef("keepImages",
                    label="Keep Images",
                    tooltip="Whether to also publish along the image sequence "
                            "next to the video reviewable.",
                    default=False),
            BoolDef("isolate",
                    label="Isolate render members of instance",
                    tooltip="When enabled only the members of the instance "
                            "will be included in the playblast review.",
                    default=False),
            BoolDef("imagePlane",
                    label="Show Image Plane",
                    default=True),
            EnumDef("transparency",
                    label="Transparency",
                    items=TRANSPARENCIES)
        ])

        return defs
