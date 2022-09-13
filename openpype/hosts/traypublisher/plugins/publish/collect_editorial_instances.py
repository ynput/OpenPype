import os
from pprint import pformat
import pyblish.api
import opentimelineio as otio


class CollectEditorialInstance(pyblish.api.InstancePlugin):
    """Collect data for instances created by settings creators."""

    label = "Collect Editorial Instances"
    order = pyblish.api.CollectorOrder - 0.1

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
        instance.context.data["editorialSourcePath"] = (
            instance.data["editorialSourcePath"])

        self.log.info(fpath)

        instance.data["stagingDir"] = os.path.dirname(fpath)

        _, ext = os.path.splitext(fpath)

        instance.data["representations"].append({
            "ext": ext[1:],
            "name": ext[1:],
            "stagingDir": instance.data["stagingDir"],
            "files": os.path.basename(fpath)
        })

        self.log.debug("Created Editorial Instance {}".format(
            pformat(instance.data)
        ))
