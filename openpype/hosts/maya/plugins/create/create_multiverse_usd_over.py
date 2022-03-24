from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseUsdOver(plugin.Creator):
    """Multiverse USD data"""

    name = "usdOverrideMain"
    label = "Multiverse USD Override"
    family = "usdOverride"
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
        self.data["numTimeSamples"] = 1
        self.data["timeSamplesSpan"] = 0.0

        # Add animation data
        animation_data = lib.collect_animation_data(True)
        self.data.update(animation_data)
