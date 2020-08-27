from maya import cmds, mel
import pymel.core as pc

from avalon import api
from avalon.maya.pipeline import containerise
from avalon.maya import lib


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

        asset = context["asset"]["name"]
        namespace = namespace or lib.unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        return containerise(
            name=name,
            namespace=namespace,
            nodes=[sound_node],
            context=context,
            loader=self.__class__.__name__
        )

    def update(self, container, representation):
        audio_node = None
        for node in pc.PyNode(container["objectName"]).members():
            if node.nodeType() == "audio":
                audio_node = node

        assert audio_node is not None, "Audio node not found."

        path = api.get_representation_path(representation)
        audio_node.filename.set(path)
        cmds.setAttr(
            container["objectName"] + ".representation",
            str(representation["_id"]),
            type="string"
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass
