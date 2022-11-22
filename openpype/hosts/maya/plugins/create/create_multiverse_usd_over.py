from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseUsdOver(plugin.Creator):
    """Create Multiverse USD Override"""

    name = "mvUsdOverrideMain"
    label = "Multiverse USD Override"
    family = "mvUsdOverride"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateMultiverseUsdOver, self).__init__(*args, **kwargs)

        # Add animation data first, since it maintains order.
        self.data.update(lib.collect_animation_data(True))

        # Order of `fileFormat` must match extract_multiverse_usd_over.py
        self.data["fileFormat"] = ["usda", "usd"]
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
