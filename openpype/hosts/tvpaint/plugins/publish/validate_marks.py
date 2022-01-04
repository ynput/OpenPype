import json

import pyblish.api
from openpype.hosts.tvpaint.api import lib


class ValidateMarksRepair(pyblish.api.Action):
    """Repair the marks."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        expected_data = ValidateMarks.get_expected_data(context)

        lib.execute_george(
            "tv_markin {} set".format(expected_data["markIn"])
        )
        lib.execute_george(
            "tv_markout {} set".format(expected_data["markOut"])
        )


class ValidateMarks(pyblish.api.ContextPlugin):
    """Validate mark in and out are enabled and it's duration.

    Mark In/Out does not have to match frameStart and frameEnd but duration is
    important.
    """

    label = "Validate Mark In/Out"
    order = pyblish.api.ValidatorOrder
    optional = True
    actions = [ValidateMarksRepair]

    @staticmethod
    def get_expected_data(context):
        scene_mark_in = context.data["sceneMarkIn"]

        # Data collected in `CollectAvalonEntities`
        frame_end = context.data["frameEnd"]
        frame_start = context.data["frameStart"]
        handle_start = context.data["handleStart"]
        handle_end = context.data["handleEnd"]

        # Calculate expeted Mark out (Mark In + duration - 1)
        expected_mark_out = (
            scene_mark_in
            + (frame_end - frame_start)
            + handle_start + handle_end
        )
        return {
            "markIn": scene_mark_in,
            "markInState": True,
            "markOut": expected_mark_out,
            "markOutState": True
        }

    def process(self, context):
        current_data = {
            "markIn": context.data["sceneMarkIn"],
            "markInState": context.data["sceneMarkInState"],
            "markOut": context.data["sceneMarkOut"],
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
