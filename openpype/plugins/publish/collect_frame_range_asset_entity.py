import pyblish.api
from openpype.pipeline import OptionalPyblishPluginMixin


class CollectFrameDataFromAssetEntity(pyblish.api.InstancePlugin,
                                      OptionalPyblishPluginMixin):
    """Collect Frame Range data From Asset Entity
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
        key_sets = []
        for key in missing_keys:
            asset_data = instance.data["assetEntity"]["data"]
            if key in asset_data:
                instance.data[key] = asset_data[key]
                key_sets.append(key)
        if key_sets:
            self.log.debug(f"Frame range data {key_sets} "
                           "has been collected from asset entity.")
