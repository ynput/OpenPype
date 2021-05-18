import os
from hiero.exporters.FnExportUtil import writeSequenceAudioWithHandles
import pyblish
import openpype


class ExtractAudioFile(openpype.api.Extractor):
    """Extracts audio subset file from all active timeline audio tracks"""

    order = pyblish.api.ExtractorOrder
    label = "Extract Subset Audio"
    hosts = ["hiero"]
    families = ["audio"]
    match = pyblish.api.Intersection

    def process(self, instance):
        # get sequence
        sequence = instance.context.data["activeSequence"]
        subset = instance.data["subset"]

        # get timeline in / out
        clip_in = instance.data["clipIn"]
        clip_out = instance.data["clipOut"]
        # get handles from context
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        staging_dir = self.staging_dir(instance)
        self.log.info("Created staging dir: {}...".format(staging_dir))

        # path to wav file
        audio_file = os.path.join(
            staging_dir, "{}.wav".format(subset)
        )

        # export audio to disk
        writeSequenceAudioWithHandles(
            audio_file,
            sequence,
            clip_in,
            clip_out,
            handle_start,
            handle_end
        )

        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        representation = {
            'files': os.path.basename(audio_file),
            'stagingDir': staging_dir,
            'name': "wav",
            'ext': "wav"
        }

        instance.data["representations"].append(representation)
