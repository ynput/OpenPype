# -*- coding: utf-8 -*-
"""Collector plugin for frames data on ROP instances."""
import hou  # noqa
import pyblish.api
from openpype.lib import BoolDef
from openpype.hosts.houdini.api import lib
from openpype.pipeline import OpenPypePyblishPluginMixin


class CollectRopFrameRange(pyblish.api.InstancePlugin,
                           OpenPypePyblishPluginMixin):

    """Collect all frames which would be saved from the ROP nodes"""

    hosts = ["houdini"]
    # This specific order value is used so that
    # this plugin runs after CollectAnatomyInstanceData
    order = pyblish.api.CollectorOrder + 0.5
    label = "Collect RopNode Frame Range"
    use_asset_handles = True

    def process(self, instance):

        node_path = instance.data.get("instance_node")
        if node_path is None:
            # Instance without instance node like a workfile instance
            self.log.debug(
                "No instance node found for instance: {}".format(instance)
            )
            return

        ropnode = hou.node(node_path)

        attr_values = self.get_attr_values_from_data(instance.data)

        if attr_values.get("use_handles", self.use_asset_handles):
            asset_data = instance.data["assetEntity"]["data"]
            handle_start = asset_data.get("handleStart", 0)
            handle_end = asset_data.get("handleEnd", 0)
        else:
            handle_start = 0
            handle_end = 0

        frame_data = lib.get_frame_data(
            ropnode, handle_start, handle_end, self.log
        )

        if not frame_data:
            return

        # Log debug message about the collected frame range
        frame_start = frame_data["frameStart"]
        frame_end = frame_data["frameEnd"]

        if attr_values.get("use_handles", self.use_asset_handles):
            self.log.debug(
                "Full Frame range with Handles "
                "[{frame_start_handle} - {frame_end_handle}]"
                .format(
                    frame_start_handle=frame_data["frameStartHandle"],
                    frame_end_handle=frame_data["frameEndHandle"]
                )
            )
        else:
            self.log.debug(
                "Use handles is deactivated for this instance, "
                "start and end handles are set to 0."
            )

        # Log collected frame range to the user
        message = "Frame range [{frame_start} - {frame_end}]".format(
            frame_start=frame_start,
            frame_end=frame_end
        )
        if handle_start or handle_end:
            message += " with handles [{handle_start}]-[{handle_end}]".format(
                handle_start=handle_start,
                handle_end=handle_end
            )
        self.log.info(message)

        if frame_data.get("byFrameStep", 1.0) != 1.0:
            self.log.info("Frame steps {}".format(frame_data["byFrameStep"]))

        instance.data.update(frame_data)

        # Add frame range to label if the instance has a frame range.
        label = instance.data.get("label", instance.data["name"])
        instance.data["label"] = (
            "{label} [{frame_start} - {frame_end}]"
            .format(
                label=label,
                frame_start=frame_start,
                frame_end=frame_end
            )
        )

    @classmethod
    def get_attribute_defs(cls):
        return [
            BoolDef("use_handles",
                    tooltip="Disable this if you want the publisher to"
                    " ignore start and end handles specified in the"
                    " asset data for this publish instance",
                    default=cls.use_asset_handles,
                    label="Use asset handles")
        ]
