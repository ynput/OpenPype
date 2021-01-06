import os

import pyblish.api
import pype.lib


class CollectTranscode(pyblish.api.InstancePlugin):
    """Collect Transcode"""

    order = pyblish.api.CollectorOrder
    label = "Collect Transcode"
    hosts = ["standalonepublisher"]
    families = ["prores422HQ", "h264"]

    # presets
    extensions = [".wav"]

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
            subsets = pype.lib.get_subsets(
                instance.context.data["assetEntity"]["name"],
                representations=[representation["ext"][1:]]
            )
            try:
                instance.data["version"] = (
                    subsets[instance.data["subset"]]["version"]["name"] + 1
                )
            except KeyError:
                pass

            # Get audio file path.
            audio_path = None
            basename = os.path.splitext(os.path.basename(file_path))[0]
            for f in os.listdir(staging_dir):
                self.log.debug(f"search file: `{f}`")
                # filter out by not sharing the same name
                if os.path.splitext(f)[0] not in basename:
                    continue
                # filter out by respected extensions
                if os.path.splitext(f)[1] not in self.extensions:
                    continue
                audio_path = os.path.join(
                    staging_dir, f
                )
                self.log.debug(f"audio_path: `{audio_path}`")
            instance.data["audioPath"] = audio_path

        representation = {
            "name": "audio",
            "ext": os.path.splitext(instance.data["audioPath"])[1],
            "files": os.path.basename(instance.data["audioPath"]),
            "stagingDir": os.path.dirname(instance.data["audioPath"]),
        }
        self.log.info(representation)
        instance.data["representations"].append(representation)
