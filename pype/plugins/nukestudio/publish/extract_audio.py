from pyblish import api
import pype


class ExtractAudioFile(pype.api.Extractor):
    """Extracts audio subset file"""

    order = api.ExtractorOrder
    label = "Extract Subset Audio"
    hosts = ["nukestudio"]
    families = ["clip", "audio"]
    match = api.Intersection

    def process(self, instance):
        import os

        from hiero.exporters.FnExportUtil import writeSequenceAudioWithHandles

        item = instance.data["item"]
        context = instance.context

        self.log.debug("creating staging dir")
        self.staging_dir(instance)

        staging_dir = instance.data["stagingDir"]

        # get handles from context
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        # get sequence from context
        sequence = context.data["activeSequence"]

        # path to wav file
        audio_file = os.path.join(
            staging_dir, "{0}.wav".format(instance.data["subset"])
        )

        # export audio to disk
        writeSequenceAudioWithHandles(
            audio_file,
            sequence,
            item.timelineIn(),
            item.timelineOut(),
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
