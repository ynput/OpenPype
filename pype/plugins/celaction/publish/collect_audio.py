import pyblish.api
from bait.paths import get_output_path
import os


class AppendCelactionAudio(pyblish.api.ContextPlugin):

    label = "Pype Audio"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        self.log.info('Collecting Audio Data')
        version = context.data('version') if context.has_data('version') else 1

        task_id = context.data["ftrackData"]["Task"]["id"]

        component_name = context.data["ftrackData"]['Shot']['name']
        version = context.data["version"]

        publish_path = get_output_path(
            task_id, component_name, version, "mov").split('/')[0:-4]

        self.log.info('publish_path: {}'.format(publish_path))

        audio_file = '/'.join(publish_path + [
            'audio',
            'audioMain',
            component_name + '_audioMain_v001.wav'
        ])

        if os.path.exists(audio_file):
            context.data["audio"] = {
                'filename': audio_file,
                'enabled': True
            }
            self.log.info(
                'audio_file: {}, has been added to context'.format(audio_file))
        else:
            self.log.warning("Couldn't find any audio file on Ftrack.")
