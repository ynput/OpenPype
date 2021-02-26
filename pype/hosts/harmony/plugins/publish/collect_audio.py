import os
import pyblish.api

import pyblish.api

class CollectAudio(pyblish.api.InstancePlugin):
    """
        Collect relative path for audio file to instance.

        Harmony api `getSoundtrackAll` returns useless path to temp folder,
        for render on farm we look into 'audio' folder and select first file.

        Correct path needs to be calculated in `submit_harmony_deadline.py`
    """

    order = pyblish.api.CollectorOrder + 0.499
    label = "Collect Audio"
    hosts = ["harmony"]
    families = ["render.farm"]

    def process(self, instance):
        full_file_name = None
        audio_dir = os.path.join(
            os.path.dirname(instance.context.data.get("currentFile")), 'audio')
        if os.path.isdir(audio_dir):
            for full_file_name in os.listdir(audio_dir):
                file_name, file_ext = os.path.splitext(full_file_name)

                if file_ext not in ['.wav', '.mp3', '.aiff']:
                    self.log.error("Unsupported file {}.{}".format(file_name,
                                                                   file_ext))
                    full_file_name = None

        if full_file_name:
            audio_file_path = os.path.join('audio', full_file_name)
            self.log.debug("audio_file_path {}".format(audio_file_path))
            instance.data["audioFile"] = audio_file_path
