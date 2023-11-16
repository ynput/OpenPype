from openpype.hosts.maya.api import plugin, lib
from openpype.lib import (
    BoolDef,
    NumberDef,
    EnumDef
)


class CreateMultiverseUsdComp(plugin.MayaCreator):
    """Create Multiverse USD Composition"""

    identifier = "io.openpype.creators.maya.mvusdcomposition"
    label = "Multiverse USD Composition"
    family = "mvUsdComposition"
    icon = "cubes"

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs(fps=True)
        defs.extend([
            EnumDef("fileFormat",
                    label="File format",
                    items=["usd", "usda"],
                    default="usd"),
            BoolDef("stripNamespaces",
                    label="Strip Namespaces",
                    default=False),
            BoolDef("mergeTransformAndShape",
                    label="Merge Transform and Shape",
                    default=False),
            BoolDef("flattenContent",
                    label="Flatten Content",
                    default=False),
            BoolDef("writeAsCompoundLayers",
                    label="Write As Compound Layers",
                    default=False),
            BoolDef("writePendingOverrides",
                    label="Write Pending Overrides",
                    default=False),
            NumberDef("numTimeSamples",
                      label="Num Time Samples",
                      default=1),
            NumberDef("timeSamplesSpan",
                      label="Time Samples Span",
                      default=0.0),
        ])

        return defs
