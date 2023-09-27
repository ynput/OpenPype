import pyblish.api
from openpype.pipeline import OptionalPyblishPluginMixin


class CollectFrameDataFromAssetEntity(
    pyblish.api.InstancePlugin,
    OptionalPyblishPluginMixin
):
    """Collect Frame Data From AssetEntity found in context

    Frame range data will only be collected if the keys
    are not yet collected for the instance.
    """

    order = pyblish.api.CollectorOrder + 0.491
    label = "Collect Frame Data From Asset"
    families = ["plate", "pointcache",
                "vdbcache", "online",
                "render"]
    hosts = ["traypublisher"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        asset_data = instance.data["assetEntity"]["data"]

        for key in (
            "fps",
            "frameStart",
            "frameEnd",
            "handleStart",
            "handleEnd"
        ):
            instance.data[key] = asset_data[key]
            self.log.debug(f"Collected Frame range data '{key}':{asset_data[key]} ")
