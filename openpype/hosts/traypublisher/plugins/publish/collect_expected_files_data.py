import pyblish.api
import clique
from openpype.pipeline import publish
from openpype.lib.transcoding import (
    VIDEO_EXTENSIONS,
    IMAGE_EXTENSIONS
)


class CollectExpectedFilesData(publish.Collector):
    """Collect Sequence Frame Data
    If the representation includes files with frame numbers,
    then set `frameStart` and `frameEnd` for the instance to the
    start and end frame respectively
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Sequence Data"
    families = [
        "plate",
        "pointcache",
        "vdbcache",
        "online",
        "render"
    ]
    hosts = ["traypublisher"]

    def process(self, instance):
        # merge VIDEO_EXTENSIONS and IMAGE_EXTENSIONS sets together
        # to get all possible extensions
        all_pixel_extensions = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS

        frame_data = self.get_frame_data_from_repre_sequence(instance)
        if not frame_data:
            # if no dict data skip collecting the frame range data
            return
        for key, value in frame_data.items():
            if key not in instance.data:
                instance.data[key] = value
                self.log.debug(f"Collected Frame range data '{key}':{value} ")

    def get_frame_data_from_repre_sequence(self, instance):
        repres = instance.data.get("representations")
        if repres:
            first_repre = repres[0]
            if "ext" not in first_repre:
                self.log.warning("Cannot find file extension"
                                 " in representation data")
                return

            files = first_repre["files"]
            collections, remainder = clique.assemble(files)
            if not collections:
                # No sequences detected and we can't retrieve
                # frame range
                self.log.debug(
                    "No sequences detected in the representation data."
                    " Skipping collecting frame range data.")
                return
            collection = collections[0]
            repres_frames = list(collection.indexes)

            return {
                "frameStart": repres_frames[0],
                "frameEnd": repres_frames[-1],
            }
