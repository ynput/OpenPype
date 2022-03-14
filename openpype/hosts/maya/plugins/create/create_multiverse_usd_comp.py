from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseUsdComp(plugin.Creator):
    """Create Multiverse USD Composition"""

    name = "usdOverrideMain"
    label = "Multiverse USD Override"
    family = "usd_override"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateMultiverseUsdComp, self).__init__(*args, **kwargs)

        self.data["stripNamespaces"] = False
        self.data["mergeTransformAndShape"] = False
        self.data["flattenContent"] = False
        self.data["writePendingOverrides"] = False

        # The attributes below are about animated cache.
        self.data["writeTimeRange"] = True
        self.data["timeRangeNumTimeSamples"] = 0
        self.data["timeRangeSamplesSpan"] = 0.0

        animation_data = lib.collect_animation_data(True)

        self.data["timeRangeStart"] = animation_data["frameStart"]
        self.data["timeRangeEnd"] = animation_data["frameEnd"]
        self.data["timeRangeIncrement"] = animation_data["step"]
        self.data["timeRangeFramesPerSecond"] = animation_data["fps"]
