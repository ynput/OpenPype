import pyblish.api


class CollectClipResolution(pyblish.api.InstancePlugin):
    """Collect clip geometry resolution"""

    order = pyblish.api.CollectorOrder + 0.101
    label = "Collect Clip Resoluton"
    hosts = ["nukestudio"]

    def process(self, instance):
        sequence = instance.context.data['activeSequence']
        resolution_width = int(sequence.format().width())
        resolution_height = int(sequence.format().height())
        pixel_aspect = sequence.format().pixelAspect()

        instance.data.update({
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "pixelAspect": pixel_aspect
        })
