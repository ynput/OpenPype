from maya import cmds, mel

from openpype.hosts.maya.api import plugin, lib
from openpype.pipeline import CreatedInstance
from openpype.lib import BoolDef, TextDef, NumberDef


class CreateShot(plugin.MayaCreator):
    """Create shots from bookmarks."""

    identifier = "io.openpype.creators.maya.shot"
    label = "Shot"
    family = "shot"
    icon = "camera"

    def get_pre_create_attr_defs(self):
        return [
            BoolDef(
                "use_selection", label="Use timeline selection", default=True
            ),
            TextDef(
                "prefix", label="Custom Prefix", placeholder="sh_"
            )
        ]

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "use_start_frame", label="Use Start Frame", default=False
            ),
            NumberDef(
                "start_frame",
                label="Start Frame",
                decimals=0,
                default=1
            ),
            BoolDef(
                "update_timeline", label="Update Timeline", default=False
            ),
            BoolDef(
                "use_handles", label="Use Handles", default=False
            ),
            NumberDef(
                "handle_start",
                label="Start Handle",
                decimals=0,
                default=5
            ),
            NumberDef(
                "handle_end",
                label="End Handle",
                decimals=0,
                default=5
            ),
        ]

    def create(self, subset_name, instance_data, pre_create_data):
        # Timeline selection can limit the instances created.
        start_frame, end_frame = cmds.timeControl(
            mel.eval('$gPlayBackSlider=$gPlayBackSlider'),
            query=True,
            rangeArray=True
        )
        nodes = []
        if pre_create_data.get("use_selection"):
            for node in cmds.ls(type="timeSliderBookmark"):
                range_start = cmds.getAttr(node + ".timeRangeStart")
                range_stop = cmds.getAttr(node + ".timeRangeStop")

                # Timeline selection is overlapping bookmark.
                if start_frame < range_start and end_frame > range_stop:
                    nodes.append(node)
                    continue

                # Timeline selection starts within a bookmark.
                if range_start < start_frame < range_stop:
                    nodes.append(node)
                    continue

                # Timeline selection ends within a bookmark.
                if range_start < end_frame < range_stop:
                    nodes.append(node)
                    continue
        else:
            nodes = cmds.ls(type="timeSliderBookmark")

        instances = []
        prefix = pre_create_data.get("prefix") or subset_name + "_"
        with lib.undo_chunk():
            for node in nodes:
                name = prefix + cmds.getAttr(node + ".name")
                instance_node = cmds.sets(node, name=name)
                instance_data["instance_node"] = instance_node
                instance = CreatedInstance(
                    self.family, name, instance_data, self
                )
                self._add_instance_to_context(instance)
                self.imprint_instance_node(
                    instance_node, data=instance.data_to_store()
                )
                instances.append(instance)

        return instances
