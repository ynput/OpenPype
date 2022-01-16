# -*- coding: utf-8 -*-
"""Validate scene settings."""
import os
import re

import pyblish.api

from openpype.hosts.aftereffects.api import get_asset_settings


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
        expected_settings = get_asset_settings()
        self.log.info("config from DB::{}".format(expected_settings))

        if any(re.search(pattern, os.getenv('AVALON_TASK'))
                for pattern in self.skip_resolution_check):
            expected_settings.pop("resolutionWidth")
            expected_settings.pop("resolutionHeight")

        if any(re.search(pattern, os.getenv('AVALON_TASK'))
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

        self.log.debug("filtered config::{}".format(expected_settings))

        current_settings = {
            "fps": fps,
            "frameStartHandle": instance.data.get("frameStartHandle"),
            "frameEndHandle": instance.data.get("frameEndHandle"),
            "resolutionWidth": instance.data.get("resolutionWidth"),
            "resolutionHeight": instance.data.get("resolutionHeight"),
            "duration": duration
        }
        self.log.info("current_settings:: {}".format(current_settings))

        invalid_settings = []
        for key, value in expected_settings.items():
            if value != current_settings[key]:
                invalid_settings.append(
                    "{} expected: {}  found: {}".format(key, value,
                                                        current_settings[key])
                )

        if ((expected_settings.get("handleStart")
            or expected_settings.get("handleEnd"))
           and invalid_settings):
            msg = "Handles included in calculation. Remove handles in DB " +\
                  "or extend frame range in Composition Setting."
            invalid_settings[-1]["reason"] = msg

        msg = "Found invalid settings:\n{}".format(
            "\n".join(invalid_settings)
        )
        assert not invalid_settings, msg
        assert os.path.exists(instance.data.get("source")), (
            "Scene file not found (saved under wrong name)"
        )
