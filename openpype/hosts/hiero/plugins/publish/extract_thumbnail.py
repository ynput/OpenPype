import os
import pyblish.api

from openpype.pipeline import publish


class ExtractThumnail(publish.Extractor):
    """
    Extractor for track item's tumnails
    """

    label = "Extract Thumnail"
    order = pyblish.api.ExtractorOrder
    families = ["plate", "take"]
    hosts = ["hiero"]

    def process(self, instance):
        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        staging_dir = self.staging_dir(instance)

        self.create_thumbnail(staging_dir, instance)

    def create_thumbnail(self, staging_dir, instance):
        track_item = instance.data["item"]
        track_item_name = track_item.name()

        # frames
        duration = track_item.sourceDuration()
        frame_start = track_item.sourceIn()
        self.log.debug(
            "__ frame_start: `{}`, duration: `{}`".format(
                frame_start, duration))

        # get thumbnail frame from the middle
        thumb_frame = int(frame_start + (duration / 2))

        thumb_file = "{}thumbnail{}{}".format(
            track_item_name, thumb_frame, ".png")
        thumb_path = os.path.join(staging_dir, thumb_file)

        thumbnail = track_item.thumbnail(thumb_frame, "colour").save(
            thumb_path,
            format='png'
        )
        self.log.debug(
            "__ thumb_path: `{}`, frame: `{}`".format(thumbnail, thumb_frame))

        self.log.info("Thumnail was generated to: {}".format(thumb_path))
        thumb_representation = {
            'files': thumb_file,
            'stagingDir': staging_dir,
            'name': "thumbnail",
            'thumbnail': True,
            'ext': "png"
        }
        instance.data["representations"].append(
            thumb_representation)
