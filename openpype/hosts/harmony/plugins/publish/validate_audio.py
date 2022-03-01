import os

import pyblish.api

import openpype.hosts.harmony.api as harmony

from openpype.pipeline import PublishXmlValidationError


class ValidateAudio(pyblish.api.InstancePlugin):
    """Ensures that there is an audio file in the scene.

    If you are sure that you want to send render without audio, you can
    disable this validator before clicking on "publish"
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Audio"
    families = ["render"]
    hosts = ["harmony"]
    optional = True

    def process(self, instance):
        node = None
        if instance.data.get("setMembers"):
            node = instance.data["setMembers"][0]

        if not node:
            return
        # Collect scene data.
        func = """function func(write_node)
        {
            return [
                sound.getSoundtrackAll().path()
            ]
        }
        func
        """
        result = harmony.send(
            {"function": func, "args": [node]}
        )["result"]

        audio_path = result[0]

        msg = "You are missing audio file:\n{}".format(audio_path)

        formatting_data = {
            "audio_url": audio_path
        }
        if os.path.isfile(audio_path):
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)
