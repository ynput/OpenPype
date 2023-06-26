import pyblish.api
import clique


class CollectFrameRangeData(pyblish.api.InstancePlugin):
    """Collect Frame Range data.
    """

    order = pyblish.api.CollectorOrder + 0.491
    label = "Collect Frame Range Data"
    families = ["plate", "pointcache",
                "vdbcache", "online",
                "render"]
    hosts = ["traypublisher"]
    img_extensions = ["exr", "dpx", "jpg", "jpeg", "png", "tiff", "tga",
                      "gif", "svg"]
    video_extensions = ["avi", "mov", "mp4"]

    def process(self, instance):
        repres = instance.data.get("representations")
        asset_data = None
        if repres:
            first_repre = repres[0]
            ext = first_repre["ext"].replace(".", "")
            if not ext or ext.lower() not in self.img_extensions:
                self.log.warning(f"Cannot find file extension "
                                 " in representation data")
                return
            if ext in self.video_extensions:
                self.log.info("Collecting frame range data"
                              " not supported for video extensions")
                return

            files = first_repre["files"]
            repres_file = clique.assemble(
                files, minimum_items=1)[0][0]
            repres_frames = [frames for frames in repres_file.indexes]
            last_frame = len(repres_frames) - 1
            asset_data = {
                "frameStart": repres_frames[0],
                "frameEnd": repres_frames[last_frame],
            }

        else:
            self.log.info("No representation data.. "
                          "\nUse Asset Entity data instead")
            asset_doc = instance.data.get("assetEntity")
            if instance.data.get("frameStart") is not None or not asset_doc:
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

        self.log.debug(f"Frame range data {key_sets} "
                       "has been collected from asset entity.")
