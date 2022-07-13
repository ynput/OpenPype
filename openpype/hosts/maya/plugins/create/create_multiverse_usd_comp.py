from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseUsdComp(plugin.Creator):
    """Create Multiverse USD Composition"""

    name = "mvUsdCompositionMain"
    label = "Multiverse USD Composition"
    family = "mvUsdComposition"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateMultiverseUsdComp, self).__init__(*args, **kwargs)

        # Add animation data first, since it maintains order.
        self.data.update(lib.collect_animation_data(True))

        # Order of `fileFormat` must match extract_multiverse_usd_comp.py
        self.data["fileFormat"] = ["usda", "usd"]
        self.data["stripNamespaces"] = False
        self.data["mergeTransformAndShape"] = False
        self.data["flattenContent"] = False
        self.data["writeAsCompoundLayers"] = False
        self.data["writePendingOverrides"] = False
        self.data["numTimeSamples"] = 1
        self.data["timeSamplesSpan"] = 0.0
