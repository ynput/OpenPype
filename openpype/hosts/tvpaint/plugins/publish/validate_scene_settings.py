import json

import pyblish.api
from openpype.pipeline import PublishXmlValidationError


# TODO @iLliCiTiT add fix action for fps
class ValidateProjectSettings(pyblish.api.ContextPlugin):
    """Validate scene settings against database."""

    label = "Validate Scene Settings"
    order = pyblish.api.ValidatorOrder
    optional = True

    def process(self, context):
        expected_data = context.data["assetEntity"]["data"]
        scene_data = {
            "fps": context.data.get("sceneFps"),
            "resolutionWidth": context.data.get("sceneWidth"),
            "resolutionHeight": context.data.get("sceneHeight"),
            "pixelAspect": context.data.get("scenePixelAspect")
        }
        invalid = {}
        for k in scene_data.keys():
            expected_value = expected_data[k]
            if scene_data[k] != expected_value:
                invalid[k] = {
                    "current": scene_data[k], "expected": expected_value
                }

        if not invalid:
            return

        raise PublishXmlValidationError(
            self,
            "Scene settings does not match database:\n{}".format(
                json.dumps(invalid, sort_keys=True, indent=4)
            ),
            formatting_data={
                "expected_fps": expected_data["fps"],
                "current_fps": scene_data["fps"],
                "expected_width": expected_data["resolutionWidth"],
                "expected_height": expected_data["resolutionHeight"],
                "current_width": scene_data["resolutionWidth"],
                "current_height": scene_data["resolutionWidth"],
                "expected_pixel_ratio": expected_data["pixelAspect"],
                "current_pixel_ratio": scene_data["pixelAspect"]
            }
        )
