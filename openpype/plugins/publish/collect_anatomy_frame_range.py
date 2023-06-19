import pyblish.api


class CollectAnatomyFrameRange(pyblish.api.InstancePlugin):
    """Collect Frame Range specific Anatomy data.

    Plugin is running for all instances on context even not active instances.
    """

    order = pyblish.api.CollectorOrder + 0.491
    label = "Collect Anatomy Frame Range"
    families = ["plate", "pointcache",
                "vdbcache", "online",
                "render"]
    hosts = ["traypublisher"]

    def process(self, instance):
        asset_doc = instance.data.get("assetEntity")
        if not asset_doc:
            self.log.debug("Instance has no asset entity set."
                           " Skipping collecting frame range data.")
            return

        asset_data = asset_doc["data"]
        key_sets = []
        for key in (
            "fps",
            "frameStart",
            "frameEnd",
            "handleStart",
            "handleEnd"
        ):
            if key not in instance.data and key in asset_data:
                instance.data[key] = asset_data[key]
                key_sets.append(key)

        self.log.debug(f"Anatomy frame range data {key_sets} "
                       "has been collected from asset entity.")
