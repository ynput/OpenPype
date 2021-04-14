import json

import pyblish.api
from avalon.tvpaint import lib


class ValidateMarksRepair(pyblish.api.Action):
    """Repair the marks."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        expected_data = ValidateMarks.get_expected_data(context)

        expected_data["markIn"] -= 1
        expected_data["markOut"] -= 1

        lib.execute_george("tv_markin {} set".format(expected_data["markIn"]))
        lib.execute_george(
            "tv_markout {} set".format(expected_data["markOut"])
        )


class ValidateMarks(pyblish.api.ContextPlugin):
    """Validate mark in and out are enabled."""

    label = "Validate Marks"
    order = pyblish.api.ValidatorOrder
    optional = True
    actions = [ValidateMarksRepair]

    @staticmethod
    def get_expected_data(context):
        return {
            "markIn": int(context.data["frameStart"]),
            "markInState": True,
            "markOut": int(context.data["frameEnd"]),
            "markOutState": True
        }

    def process(self, context):
        current_data = {
            "markIn": context.data["sceneMarkIn"] + 1,
            "markInState": context.data["sceneMarkInState"],
            "markOut": context.data["sceneMarkOut"] + 1,
            "markOutState": context.data["sceneMarkOutState"]
        }
        expected_data = self.get_expected_data(context)
        invalid = {}
        for k in current_data.keys():
            if current_data[k] != expected_data[k]:
                invalid[k] = {
                    "current": current_data[k],
                    "expected": expected_data[k]
                }

        if invalid:
            raise AssertionError(
                "Marks does not match database:\n{}".format(
                    json.dumps(invalid, sort_keys=True, indent=4)
                )
            )
