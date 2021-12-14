import pyblish.api


class ValidateWorkfileData(pyblish.api.ContextPlugin):
    """Validate mark in and out are enabled and it's duration.

    Mark In/Out does not have to match frameStart and frameEnd but duration is
    important.
    """

    label = "Validate Workfile Data"
    order = pyblish.api.ValidatorOrder
    targets = ["tvpaint_worker"]

    def process(self, context):
        # Data collected in `CollectAvalonEntities`
        frame_start = context.data["frameStart"]
        frame_end = context.data["frameEnd"]
        handle_start = context.data["handleStart"]
        handle_end = context.data["handleEnd"]

        scene_data = context.data["sceneData"]
        scene_mark_in = scene_data["sceneMarkIn"]
        scene_mark_out = scene_data["sceneMarkOut"]

        expected_range = (
            (frame_end - frame_start + 1)
            + handle_start
            + handle_end
        )
        marks_range = scene_mark_out - scene_mark_in + 1
        if expected_range != marks_range:
            raise AssertionError((
                "Wrong Mark In/Out range."
                " Expected range is {} frames got {} frames"
            ).format(expected_range, marks_range))
