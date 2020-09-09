import json

import pyblish.api

import avalon.harmony
import pype.hosts.harmony


class ValidateSceneSettingsRepair(pyblish.api.Action):
    """Repair the instance."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        pype.hosts.harmony.set_scene_settings(
            pype.hosts.harmony.get_asset_settings()
        )


class ValidateSceneSettings(pyblish.api.InstancePlugin):
    """Ensure the scene settings are in sync with database."""

    order = pyblish.api.ValidatorOrder
    label = "Validate Scene Settings"
    families = ["workfile"]
    hosts = ["harmony"]
    actions = [ValidateSceneSettingsRepair]

    frame_check_filter = ["_ch_", "_pr_", "_intd_", "_extd_"]

    def process(self, instance):
        expected_settings = pype.hosts.harmony.get_asset_settings()
        self.log.info(expected_settings)

        # Harmony is expected to start at 1.
        frame_start = expected_settings["frameStart"]
        frame_end = expected_settings["frameEnd"]
        expected_settings["frameEnd"] = frame_end - frame_start + 1
        expected_settings["frameStart"] = 1

        self.log.info(instance.context.data['anatomyData']['asset'])

        if any(string in instance.context.data['anatomyData']['asset']
                for string in self.frame_check_filter):
            expected_settings.pop("frameEnd")

        func = """function func()
        {
            return {
                "fps": scene.getFrameRate(),
                "frameStart": scene.getStartFrame(),
                "frameEnd": scene.getStopFrame(),
                "resolutionWidth": scene.defaultResolutionX(),
                "resolutionHeight": scene.defaultResolutionY()
            };
        }
        func
        """
        current_settings = avalon.harmony.send({"function": func})["result"]

        invalid_settings = []
        for key, value in expected_settings.items():
            if value != current_settings[key]:
                invalid_settings.append({
                    "name": key,
                    "expected": value,
                    "current": current_settings[key]
                })

        msg = "Found invalid settings:\n{}".format(
            json.dumps(invalid_settings, sort_keys=True, indent=4)
        )
        assert not invalid_settings, msg
