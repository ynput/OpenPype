import os

import pyblish.api
from openpype import api


class CollectTranscode(pyblish.api.InstancePlugin):
    """Collect Transcode"""

    order = pyblish.api.CollectorOrder
    label = "Collect Transcode"
    hosts = ["traypublisher"]
    families = ["transcode"]

    # presets
    audio_extensions = [".wav"]

    def process(self, instance):
        self.log.debug(f"instance: `{instance}`")
        import pprint
        self.log.debug("{}".format(pprint.pformat(instance.data, indent=4)))
        # get representation with editorial file
        audio_path = None
        source_file_info = instance.data["creator_attributes"]["filepath"]
        source_file_name = source_file_info["filenames"][0]
        # make editorial sequence file path
        staging_dir = source_file_info["directory"]
        instance.data["stagingDir"] = staging_dir
        file_path = os.path.join(
            staging_dir, source_file_name
        )
        instance.context.data["currentFile"] = file_path
        name = os.path.splitext(source_file_name)[0]
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
        for f in os.listdir(staging_dir):
            self.log.debug(f"search file: `{f}`")
            # filter out by not sharing the same name
            if os.path.splitext(f)[0] not in name:
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
