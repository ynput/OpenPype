import os

import pyblish.api
from pype import api


class CollectTranscode(pyblish.api.InstancePlugin):
    """Collect Transcode"""

    order = pyblish.api.CollectorOrder
    label = "Collect Transcode"
    hosts = ["standalonepublisher"]
    families = ["prores422HQ", "proresProxy", "h264"]

    # presets
    audio_extensions = [".wav"]

    def process(self, instance):
        self.log.debug(f"instance: `{instance}`")
        # get representation with editorial file
        for representation in instance.data["representations"]:
            self.log.debug(f"representation: `{representation}`")
            # make editorial sequence file path
            staging_dir = representation["stagingDir"]
            instance.data["stagingDir"] = staging_dir
            file_path = os.path.join(
                staging_dir, str(representation["files"])
            )
            instance.context.data["currentFile"] = file_path
            name = os.path.splitext(os.path.basename(file_path))[0]
            instance.data["name"] = name
            instance.data["label"] = name
            instance.data["families"].append("transcode")

            # Get version from published versions.
            instance.data["version"] = 1

            version = api.get_latest_version(
                instance.data["asset"], instance.data["subset"]
            )

            if version:
                instance.data["version"] = version["name"] + 1

            self.log.info(
                "Setting version to: {}".format(instance.data["version"])
            )

            # Get audio file path.
            audio_path = None
            basename = os.path.splitext(os.path.basename(file_path))[0]
            for f in os.listdir(staging_dir):
                self.log.debug(f"search file: `{f}`")
                # filter out by not sharing the same name
                if os.path.splitext(f)[0] not in basename:
                    continue
                # filter out by respected audio_extensions
                if os.path.splitext(f)[1] not in self.audio_extensions:
                    continue
                audio_path = os.path.join(
                    staging_dir, f
                )
                self.log.debug(f"audio_path: `{audio_path}`")
            instance.data["audioPath"] = audio_path

        if audio_path:
            representation = {
                "name": "audio",
                "ext": os.path.splitext(instance.data["audioPath"])[1],
                "files": os.path.basename(instance.data["audioPath"]),
                "stagingDir": os.path.dirname(instance.data["audioPath"]),
            }
            self.log.info(representation)
            instance.data["representations"].append(representation)
