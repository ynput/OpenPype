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

    useMayaTimeline = True
    panZoom = False

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs()

        # Option for using Maya or asset frame range in settings.
        if not self.useMayaTimeline:
            # Update the defaults to be the asset frame range
            frame_range = lib.get_frame_range()
            defs_by_key = {attr_def.key: attr_def for attr_def in defs}
            for key, value in frame_range.items():
                if key not in defs_by_key:
                    raise RuntimeError("Attribute definition not found to be "
                                       "updated for key: {}".format(key))
                attr_def = defs_by_key[key]
                attr_def.default = value

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
                    items=TRANSPARENCIES),
            BoolDef("panZoom",
                    label="Enable camera pan/zoom",
                    default=True),
        ])

        return defs
