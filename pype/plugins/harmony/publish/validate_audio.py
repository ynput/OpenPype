import json
import os

import pyblish.api

import avalon.harmony
import pype.hosts.harmony


class ValidateAudio(pyblish.api.InstancePlugin):
    """Ensures that there is an audio file in the scene. If you are sure that you want to send render without audio, you can disable this validator before clicking on "publish" """

    order = pyblish.api.ValidatorOrder
    label = "Validate Audio"
    families = ["render"]
    hosts = ["harmony"]
    optional = True

    def process(self, instance):
        # Collect scene data.
        func = """function func(write_node)
        {
            return [
                sound.getSoundtrackAll().path()
            ]
        }
        func
        """
        result = avalon.harmony.send(
            {"function": func, "args": [instance[0]]}
        )["result"]

        audio_path = result[0]

        msg = "You are missing audio file:\n{}".format(audio_path)

        assert os.path.isfile(audio_path), msg
