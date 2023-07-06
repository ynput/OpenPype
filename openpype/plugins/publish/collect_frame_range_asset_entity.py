import pyblish.api
from openpype.pipeline import OptionalPyblishPluginMixin


class CollectFrameDataFromAssetEntity(pyblish.api.InstancePlugin,
                                      OptionalPyblishPluginMixin):
    """Collect Frame Range data From Asset Entity

    Frame range data will only be collected if the keys
    are not yet collected for the instance.
    """

    order = pyblish.api.CollectorOrder + 0.3
    label = "Collect Frame Data From Asset Entity"
    families = ["plate", "pointcache",
                "vdbcache", "online",
                "render"]
    hosts = ["traypublisher"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
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
