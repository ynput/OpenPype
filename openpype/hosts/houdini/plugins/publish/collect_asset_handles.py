# -*- coding: utf-8 -*-
"""Collector plugin for frames data on ROP instances."""
import hou  # noqa
import pyblish.api
from openpype.lib import BoolDef
from openpype.pipeline import OpenPypePyblishPluginMixin


class CollectAssetHandles(pyblish.api.InstancePlugin,
                          OpenPypePyblishPluginMixin):
    """Apply asset handles.

    If instance does not have:
        - frameStart
        - frameEnd
        - handleStart
        - handleEnd
    But it does have:
        - frameStartHandle
        - frameEndHandle

    Then we will retrieve the asset's handles to compute
    the exclusive frame range and actual handle ranges.
    """

    hosts = ["houdini"]

    # This specific order value is used so that
    # this plugin runs after CollectAnatomyInstanceData
    order = pyblish.api.CollectorOrder + 0.499

    label = "Collect Asset Handles"
    use_asset_handles = True

    def process(self, instance):
        # Only process instances without already existing handles data
        # but that do have frameStartHandle and frameEndHandle defined
        # like the data collected from CollectRopFrameRange
        if "frameStartHandle" not in instance.data:
            return
        if "frameEndHandle" not in instance.data:
            return

        has_existing_data = {
            "handleStart",
            "handleEnd",
            "frameStart",
            "frameEnd"
        }.issubset(instance.data)
        if has_existing_data:
            return

        attr_values = self.get_attr_values_from_data(instance.data)
        if attr_values.get("use_handles", self.use_asset_handles):
            asset_data = instance.data["assetEntity"]["data"]
            handle_start = asset_data.get("handleStart", 0)
            handle_end = asset_data.get("handleEnd", 0)
        else:
            handle_start = 0
            handle_end = 0

        frame_start = instance.data["frameStartHandle"] + handle_start
        frame_end = instance.data["frameEndHandle"] - handle_end

        instance.data.update({
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStart": frame_start,
            "frameEnd": frame_end
        })

        # Log debug message about the collected frame range
        if attr_values.get("use_handles", self.use_asset_handles):
            self.log.debug(
                "Full Frame range with Handles "
                "[{frame_start_handle} - {frame_end_handle}]"
                .format(
                    frame_start_handle=instance.data["frameStartHandle"],
                    frame_end_handle=instance.data["frameEndHandle"]
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

        if instance.data.get("byFrameStep", 1.0) != 1.0:
            self.log.info(
                "Frame steps {}".format(instance.data["byFrameStep"]))

        # Add frame range to label if the instance has a frame range.
        label = instance.data.get("label", instance.data["name"])
        instance.data["label"] = (
            "{label} [{frame_start_handle} - {frame_end_handle}]"
            .format(
                label=label,
                frame_start_handle=instance.data["frameStartHandle"],
                frame_end_handle=instance.data["frameEndHandle"]
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
