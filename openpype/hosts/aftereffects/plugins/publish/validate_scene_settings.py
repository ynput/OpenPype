# -*- coding: utf-8 -*-
"""Validate scene settings."""
import os
import re

import pyblish.api
from openpype.lib import get_frame_info


class ValidateSceneSettings(pyblish.api.InstancePlugin):
    """
        Ensures that Composition Settings (right mouse on comp) are same as
        in FTrack on task.

        By default checks only duration - how many frames should be rendered.
        Compares:
            Frame start - Frame end + 1 from FTrack
                against
            Duration in Composition Settings.

        If this complains:
            Check error message where is discrepancy.
            Check FTrack task 'pype' section of task attributes for expected
            values.
            Check/modify rendered Composition Settings.

        If you know what you are doing run publishing again, uncheck this
        validation before Validation phase.
    """

    """
        Dev docu:
        Could be configured by 'presets/plugins/aftereffects/publish'

        skip_timelines_check - fill task name for which skip validation of
            frameStart
            frameEnd
            fps
            handleStart
            handleEnd
        skip_resolution_check - fill entity type ('asset') to skip validation
            resolutionWidth
            resolutionHeight
            TODO support in extension is missing for now

         By defaults validates duration (how many frames should be published)
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Scene Settings"
    families = ["render.farm", "render"]
    hosts = ["aftereffects"]
    optional = True

    skip_timelines_check = [".*"]  # * >> skip for all
    skip_resolution_check = [".*"]

    def process(self, instance):
        """Plugin entry point."""
        asset_doc = instance.data.get("AssetEntity")
        if asset_doc is None:
            asset_doc = instance.context.data.get("AssetEntity")

        asset_data = asset_doc["data"]
        fps = asset_data.get("fps")
        resolution_width = asset_data.get("resolutionWidth")
        resolution_height = asset_data.get("resolutionHeight")

        anatomy = instance.context.data.get("anatomy")
        frame_info = get_frame_info(asset_doc, anatomy)

        expected_settings = {
            "fps": fps,
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "frameStartHandle": frame_info.handle_frame_start,
            "frameEndHandle": frame_info.handle_frame_end,
            "duration": frame_info.frame_range
        }

        self.log.info("config from DB::{}".format(expected_settings))

        if any(re.search(pattern, os.getenv('AVALON_TASK'))
                for pattern in self.skip_resolution_check):
            expected_settings.pop("resolutionWidth")
            expected_settings.pop("resolutionHeight")

        if any(re.search(pattern, os.getenv('AVALON_TASK'))
                for pattern in self.skip_timelines_check):
            expected_settings.pop('fps', None)
            expected_settings.pop('frameStartHandle', None)
            expected_settings.pop('frameEndHandle', None)

        # handle case where ftrack uses only two decimal places
        # 23.976023976023978 vs. 23.98
        fps = instance.data.get("fps")
        if fps:
            if isinstance(fps, float):
                fps = float("{:.2f}".format(fps))
            expected_settings["fps"] = fps

        self.log.debug("filtered config::{}".format(expected_settings))

        scene_frame_start = instance.data["frameStartHandle"]
        scene_frame_end = instance.data["frameEndHandle"]
        current_settings = {
            "fps": fps,
            "resolutionWidth": instance.data.get("resolutionWidth"),
            "resolutionHeight": instance.data.get("resolutionHeight"),
            "frameStartHandle": scene_frame_start,
            "frameEndHandle": scene_frame_end,
            "duration": scene_frame_end - scene_frame_start + 1
        }
        self.log.info("current_settings:: {}".format(current_settings))

        invalid_settings = []
        handles_info_added = False
        for key, value in expected_settings.items():
            current_value = current_settings[key]
            if value == current_value:
                continue

            msg = "{} expected: {} found: {}".format(
                key, value, current_value
            )
            if (
                not handles_info_added
                and key in ("frameStartHandle", "frameEndHandle")
            ):
                handles_info_added = True
                msg += (
                    " Handles included in calculation. Remove handles in DB "
                    "or extend frame range in Composition Setting."
                )
            invalid_settings.append(msg)

        msg = "Found invalid settings:\n{}".format(
            "\n".join(invalid_settings)
        )
        assert not invalid_settings, msg
        assert os.path.exists(instance.data.get("source")), (
            "Scene file not found (saved under wrong name)"
        )
