import pyblish.api


class CollectFrameDataFromAssetEntity(pyblish.api.InstancePlugin):
    """Collect Frame Data From AssetEntity found in context

    Frame range data will only be collected if the keys
    are not yet collected for the instance.
    """

    order = pyblish.api.CollectorOrder + 0.491
    label = "Collect Missing Frame Data From Asset"
    families = ["plate", "pointcache",
                "vdbcache", "online",
                "render"]
    hosts = ["traypublisher"]

    def process(self, instance):
        missing_keys = []
        for key in (
            "fps",
            "frameStart",
            "frameEnd",
            "handleStart",
            "handleEnd"
        ):
            if key not in instance.data:
                missing_keys.append(key)
        keys_set = []
        for key in missing_keys:
            asset_data = instance.data["assetEntity"]["data"]
            if key in asset_data:
                instance.data[key] = asset_data[key]
                keys_set.append(key)
        if keys_set:
            self.log.debug(f"Frame range data {keys_set} "
                           "has been collected from asset entity.")
