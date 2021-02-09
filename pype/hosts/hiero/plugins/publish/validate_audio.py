import pyblish
from pype.hosts.hiero.api import is_overlapping


class ValidateAudioFile(pyblish.api.InstancePlugin):
    """Validate audio subset has avilable audio track clips"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Audio Tracks"
    hosts = ["hiero"]
    families = ["audio"]

    def process(self, instance):
        clip = instance.data["item"]
        audio_tracks = instance.context.data["audioTracks"]
        audio_clip = None

        for a_track in audio_tracks:
            for item in a_track.items():
                if is_overlapping(item, clip):
                    audio_clip = item

        assert audio_clip, "Missing relative audio clip for clip {}".format(
            clip.name()
        )
