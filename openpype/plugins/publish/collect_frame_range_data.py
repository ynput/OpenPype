import pyblish.api
import clique
from openpype.pipeline import publish
from openpype.lib import BoolDef
from openpype.lib.transcoding import IMAGE_EXTENSIONS


class CollectFrameRangeData(pyblish.api.InstancePlugin,
                            publish.OpenPypePyblishPluginMixin):
    """Collect Frame Range data.
    """

    order = pyblish.api.CollectorOrder + 0.491
    label = "Collect Frame Range Data"
    families = ["plate", "pointcache",
                "vdbcache", "online",
                "render"]
    hosts = ["traypublisher"]

    def process(self, instance):
        repres = instance.data.get("representations")
        asset_data = None
        if repres:
            first_repre = repres[0]
            ext = ".{}".format(first_repre["ext"])
            if "ext" not in first_repre:
                self.log.warning(f"Cannot find file extension"
                                 " in representation data")
                return
            if ext not in IMAGE_EXTENSIONS:
                self.log.info("Collecting frame range data"
                              " only supported for image extensions")
                return

            files = first_repre["files"]
            repres_files, remainder = clique.assemble(files)
            repres_frames = list()
            for repres_file in repres_files:
                repres_frames = list(repres_file.indexes)
            asset_data = {
                "frameStart": repres_frames[0],
                "frameEnd": repres_frames[-1],
            }

        else:
            self.log.info(
                "No representation data.. Use Asset Entity data instead")
            asset_doc = instance.data.get("assetEntity")

            attr_values = self.get_attr_values_from_data(instance.data)
            if attr_values.get("setAssetFrameRange", True):
                if instance.data.get("frameStart") is not None or not asset_doc:
                    self.log.debug("Instance has no asset entity set."
                                " Skipping collecting frame range data.")
                    return
                self.log.debug(
                    "Falling back to collect frame range"
                    " data from asset entity set.")
                asset_data = asset_doc["data"]
            else:
                self.log.debug("Skipping collecting frame range data.")
                return

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

        self.log.debug(f"Frame range data {key_sets} "
                       "has been collected from asset entity.")

    @classmethod
    def get_attribute_defs(cls):
        return [
            BoolDef("setAssetFrameRange",
                    label="Set Asset Frame Range",
                    default=False),
        ]
