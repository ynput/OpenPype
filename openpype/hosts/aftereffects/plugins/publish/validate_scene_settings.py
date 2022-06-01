# -*- coding: utf-8 -*-
"""Validate scene settings."""
import os
import re

import pyblish.api

from openpype.pipeline import (
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)
from openpype.hosts.aftereffects.api import get_asset_settings


class ValidateSceneSettings(OptionalPyblishPluginMixin,
                            pyblish.api.InstancePlugin):
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
        # Skip the instance if is not active by data on the instance
        if not self.is_active(instance.data):
            return

        expected_settings = get_asset_settings()
        self.log.info("config from DB::{}".format(expected_settings))

        task_name = instance.data["anatomyData"]["task"]["name"]
        if any(re.search(pattern, task_name)
                for pattern in self.skip_resolution_check):
            expected_settings.pop("resolutionWidth")
            expected_settings.pop("resolutionHeight")

        if any(re.search(pattern, task_name)
                for pattern in self.skip_timelines_check):
            expected_settings.pop('fps', None)
            expected_settings.pop('frameStart', None)
            expected_settings.pop('frameEnd', None)
            expected_settings.pop('handleStart', None)
            expected_settings.pop('handleEnd', None)

        # handle case where ftrack uses only two decimal places
        # 23.976023976023978 vs. 23.98
        fps = instance.data.get("fps")
        if fps:
            if isinstance(fps, float):
                fps = float(
                    "{:.2f}".format(fps))
            expected_settings["fps"] = fps

        duration = instance.data.get("frameEndHandle") - \
            instance.data.get("frameStartHandle") + 1

        self.log.debug("validated items::{}".format(expected_settings))

        current_settings = {
            "fps": fps,
            "frameStart": instance.data.get("frameStart"),
            "frameEnd": instance.data.get("frameEnd"),
            "handleStart": instance.data.get("handleStart"),
            "handleEnd": instance.data.get("handleEnd"),
            "frameStartHandle": instance.data.get("frameStartHandle"),
            "frameEndHandle": instance.data.get("frameEndHandle"),
            "resolutionWidth": instance.data.get("resolutionWidth"),
            "resolutionHeight": instance.data.get("resolutionHeight"),
            "duration": duration
        }
        self.log.info("current_settings:: {}".format(current_settings))

        invalid_settings = []
        invalid_keys = set()
        for key, value in expected_settings.items():
            if value != current_settings[key]:
                msg = "'{}' expected: '{}'  found: '{}'".format(
                    key, value, current_settings[key])

                if key == "duration" and expected_settings.get("handleStart"):
                    msg += "Handles included in calculation. Remove " \
                           "handles in DB or extend frame range in " \
                           "Composition Setting."

                invalid_settings.append(msg)
                invalid_keys.add(key)

        if invalid_settings:
            msg = "Found invalid settings:\n{}".format(
                "\n".join(invalid_settings)
            )

            invalid_keys_str = ",".join(invalid_keys)
            break_str = "<br/>"
            invalid_setting_str = "<b>Found invalid settings:</b><br/>{}".\
                format(break_str.join(invalid_settings))

            formatting_data = {
                "invalid_setting_str": invalid_setting_str,
                "invalid_keys_str": invalid_keys_str
            }
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)

        if not os.path.exists(instance.data.get("source")):
            scene_url = instance.data.get("source")
            msg = "Scene file {} not found (saved under wrong name)".format(
                scene_url
            )
            formatting_data = {
                "scene_url": scene_url
            }
            raise PublishXmlValidationError(self, msg, key="file_not_found",
                                            formatting_data=formatting_data)
