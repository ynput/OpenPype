from maya import cmds, mel

from avalon import api


class AudioLoader(api.Loader):
    """Specific loader of audio."""

    families = ["audio"]
    label = "Import audio."
    representations = ["wav"]
    icon = "volume-up"
    color = "orange"

    def load(self, context, name, namespace, data):
        start_frame = cmds.playbackOptions(query=True, min=True)
        sound_node = cmds.sound(
            file=context["representation"]["data"]["path"], offset=start_frame
        )
        cmds.timeControl(
            mel.eval("$tmpVar=$gPlayBackSlider"),
            edit=True,
            sound=sound_node,
            displaySound=True
        )

        return [sound_node]
