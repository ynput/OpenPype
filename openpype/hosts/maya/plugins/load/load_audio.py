from maya import cmds, mel

from openpype.client import (
    get_asset_by_id,
    get_subset_by_id,
    get_version_by_id,
)
from openpype.pipeline import (
    get_current_project_name,
    load,
    get_representation_path,
)
from openpype.hosts.maya.api.pipeline import containerise
from openpype.hosts.maya.api.lib import unique_namespace, get_container_members


class AudioLoader(load.LoaderPlugin):
    """Specific loader of audio."""

    families = ["audio"]
    label = "Import audio"
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
        namespace = namespace or unique_namespace(
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

        members = get_container_members(container)
        audio_nodes = cmds.ls(members, type="audio")

        assert audio_nodes is not None, "Audio node not found."
        audio_node = audio_nodes[0]

        path = get_representation_path(representation)
        cmds.setAttr("{}.filename".format(audio_node), path, type="string")

        cmds.timeControl(
            mel.eval("$tmpVar=$gPlayBackSlider"),
            edit=True,
            sound=audio_node,
            displaySound=True
        )

        cmds.setAttr(
            container["objectName"] + ".representation",
            str(representation["_id"]),
            type="string"
        )

        # Set frame range.
        project_name = get_current_project_name()
        version = get_version_by_id(
            project_name, representation["parent"], fields=["parent"]
        )
        subset = get_subset_by_id(
            project_name, version["parent"], fields=["parent"]
        )
        asset = get_asset_by_id(
            project_name, subset["parent"], fields=["parent", "data"]
        )

        source_start = 1 - asset["data"]["frameStart"]
        source_end = asset["data"]["frameEnd"]

        cmds.setAttr("{}.sourceStart".format(audio_node), source_start)
        cmds.setAttr("{}.sourceEnd".format(audio_node), source_end)

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
