import os
from pprint import pformat
import pyblish.api
import opentimelineio as otio


class CollectSettingsSimpleInstances(pyblish.api.InstancePlugin):
    """Collect data for instances created by settings creators."""

    label = "Collect Editorial Instances"
    order = pyblish.api.CollectorOrder

    hosts = ["traypublisher"]
    families = ["editorial"]

    def process(self, instance):

        if "families" not in instance.data:
            instance.data["families"] = []

        if "representations" not in instance.data:
            instance.data["representations"] = []

        fpath = instance.data["sequenceFilePath"]
        otio_timeline_string = instance.data.pop("otioTimeline")
        otio_timeline = otio.adapters.read_from_string(
            otio_timeline_string)

        instance.context.data["otioTimeline"] = otio_timeline

        self.log.info(fpath)

        instance.data["stagingDir"] = os.path.dirname(fpath)

        _, ext = os.path.splitext(fpath)

        instance.data["representations"].append({
            "ext": ext[1:],
            "name": ext[1:],
            "stagingDir": instance.data["stagingDir"],
            "files": os.path.basename(fpath)
        })

        self.log.debug("Created Simple Settings instance {}".format(
            pformat(instance.data)
        ))
