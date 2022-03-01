import pyblish.api


class CollectClipResolution(pyblish.api.InstancePlugin):
    """Collect clip geometry resolution"""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Collect Clip Resolution"
    hosts = ["hiero"]
    families = ["clip"]

    def process(self, instance):
        sequence = instance.context.data['activeSequence']
        item = instance.data["item"]
        source_resolution = instance.data.get("sourceResolution", None)

        resolution_width = int(sequence.format().width())
        resolution_height = int(sequence.format().height())
        pixel_aspect = sequence.format().pixelAspect()

        # source exception
        if source_resolution:
            resolution_width = int(item.source().mediaSource().width())
            resolution_height = int(item.source().mediaSource().height())
            pixel_aspect = item.source().mediaSource().pixelAspect()

        resolution_data = {
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "pixelAspect": pixel_aspect
        }
        # add to instacne data
        instance.data.update(resolution_data)

        self.log.info("Resolution of instance '{}' is: {}".format(
            instance,
            resolution_data
        ))
