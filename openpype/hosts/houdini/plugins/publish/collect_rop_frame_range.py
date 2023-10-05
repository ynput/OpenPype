# -*- coding: utf-8 -*-
"""Collector plugin for frames data on ROP instances."""
import hou  # noqa
import pyblish.api
from openpype.lib import BoolDef
from openpype.hosts.houdini.api import lib
from openpype.pipeline import OptionalPyblishPluginMixin


class CollectRopFrameRange(pyblish.api.InstancePlugin,
                           OptionalPyblishPluginMixin):

    """Collect all frames which would be saved from the ROP nodes"""

    hosts = ["houdini"]
    order = pyblish.api.CollectorOrder
    label = "Collect RopNode Frame Range"

    def process(self, instance):

        node_path = instance.data.get("instance_node")
        if node_path is None:
            # Instance without instance node like a workfile instance
            self.log.debug(
                "No instance node found for instance: {}".format(instance)
            )
            return

        ropnode = hou.node(node_path)
        asset_data = instance.context.data["assetEntity"]["data"]

        attr_values = self.get_attr_values_from_data(instance.data)
        if not attr_values.get("use_handles"):
            asset_data["handleStart"] = 0
            asset_data["handleEnd"] = 0

        frame_data = lib.get_frame_data(ropnode, asset_data, self.log)

        if not frame_data:
            return

        # Log artist friendly message about the collected frame range
        message = ""

        if attr_values.get("use_handles"):
            message += (
                "Full Frame range with Handles "
                "{0[frameStartHandle]} - {0[frameEndHandle]}\n"
                .format(frame_data)
            )
        else:
            message += (
                "Use handles is deactivated for this instance, "
                "start and end handles are set to 0.\n"
            )

        message += (
            "Frame range {0[frameStart]} - {0[frameEnd]}"
            .format(frame_data)
        )

        if frame_data.get("byFrameStep", 1.0) != 1.0:
            message += "\nFrame steps {0[byFrameStep]}".format(frame_data)

        self.log.info(message)

        instance.data.update(frame_data)

        # Add frame range to label if the instance has a frame range.
        label = instance.data.get("label", instance.data["name"])
        instance.data["label"] = (
            "{0} [{1[frameStart]} - {1[frameEnd]}]"
            .format(label, frame_data)
        )

    @classmethod
    def get_attribute_defs(cls):
        return [
            BoolDef("use_handles",
                    tooltip="Disable this if you don't want the publisher"
                    " to ignore start and end handles specified in the asset data"
                    " for this publish instance",
                    default=True,
                    label="Use asset handles")
        ]
