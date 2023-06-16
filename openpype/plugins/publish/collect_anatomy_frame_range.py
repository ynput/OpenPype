import pyblish.api


class CollectAnatomyFrameRange(pyblish.api.InstancePlugin):
    """Collect Frame Range specific Anatomy data.

    Plugin is running for all instances on context even not active instances.
    """

    order = pyblish.api.CollectorOrder + 0.491
    label = "Collect Anatomy Frame Range"
    hosts = ["traypublisher"]

    def process(self, instance):
        self.log.info("Collecting Anatomy frame range.")
        asset_doc = instance.data.get("assetEntity")
        if not asset_doc:
            self.log.info("Missing required data..")
            return

        asset_data = asset_doc["data"]
        for key in (
            "fps",
            "frameStart",
            "frameEnd",
            "handleStart",
            "handleEnd"
        ):
            if key not in instance.data and key in asset_data:
                value = asset_data[key]
                instance.data[key] = value

        self.log.info("Anatomy frame range collection finished.")
