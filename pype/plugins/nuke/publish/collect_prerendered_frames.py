import pyblish.api
import os

class CollectFrames(pyblish.api.InstancePlugin):
    """Inject the host into context"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Collect data into prerenderd frames"
    hosts = ["nuke"]
    families = ['prerendered.frames']

    def process(self, instance):

        collected_frames = os.listdir(instance.data['outputDir'])

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(collected_frames)
        instance.data['stagingDir'] = instance.data['outputDir']
        instance.data['transfer'] = False

        self.log.info('collected frames: {}'.format(collected_frames))
