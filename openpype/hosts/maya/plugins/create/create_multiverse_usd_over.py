from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseUsdOver(plugin.Creator):
    """Multiverse USD data"""

    name = "usdOverrideMain"
    label = "Multiverse USD Override"
    family = "usd_override"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateMultiverseUsdOver, self).__init__(*args, **kwargs)

        self.data["writeAll"] = False
        self.data["writeTransforms"] = True
        self.data["writeVisibility"] = True
        self.data["writeAttributes"] = True
        self.data["writeMaterials"] = True
        self.data["writeVariants"] = True
        self.data["writeVariantsDefinition"] = True
        self.data["writeActiveState"] = True
        self.data["writeNamespaces"] = False

        # The attributes below are about animated cache.
        self.data["writeTimeRange"] = True
        self.data["timeRangeNumTimeSamples"] = 0
        self.data["timeRangeSamplesSpan"] = 0.0

        animation_data = lib.collect_animation_data(True)

        self.data["timeRangeStart"] = animation_data["frameStart"]
        self.data["timeRangeEnd"] = animation_data["frameEnd"]
        self.data["timeRangeIncrement"] = animation_data["step"]
        self.data["timeRangeFramesPerSecond"] = animation_data["fps"]
