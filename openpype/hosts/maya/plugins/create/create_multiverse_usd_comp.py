from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseUsdComp(plugin.Creator):
    """Create Multiverse USD Composition"""

    name = "usdCompositionMain"
    label = "Multiverse USD Composition"
    family = "usdComposition"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateMultiverseUsdComp, self).__init__(*args, **kwargs)

        self.data["stripNamespaces"] = False
        self.data["mergeTransformAndShape"] = False
        self.data["flattenContent"] = False
        self.data["writePendingOverrides"] = False
        self.data["numTimeSamples"] = 1
        self.data["timeSamplesSpan"] = 0.0

        # Add animation data
        animation_data = lib.collect_animation_data(True)
        self.data.update(animation_data)
