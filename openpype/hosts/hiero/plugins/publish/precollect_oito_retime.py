from pyblish import api
from openpype.lib import editorial
reload(editorial)


class PrecollectOTIORetime(api.InstancePlugin):
    """Calculate Retiming of selected track items."""

    order = api.CollectorOrder - 0.578
    label = "Precollect OTIO Retime"
    hosts = ["hiero"]
    families = ["clip"]

    def process(self, instance):
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        # get basic variables
        otio_clip = instance.data["otioClip"]
        retimed_attributes = editorial.get_media_range_with_retimes(
            otio_clip, handle_start, handle_end)
        self.log.debug(
            ">> media_in, media_out: {}".format(retimed_attributes))

        media_in = retimed_attributes["mediaIn"]
        media_out = retimed_attributes["mediaOut"]
        handles_start = retimed_attributes["handleStart"]
        handles_end = retimed_attributes["handleEnd"]
