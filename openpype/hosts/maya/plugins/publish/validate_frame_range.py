import pyblish.api
import openpype.api

from maya import cmds


class ValidateFrameRange(pyblish.api.InstancePlugin):
    """Validates the frame ranges.

    This is an optional validator checking if the frame range on instance
    matches the frame range specified for the asset.

    It also validates render frame ranges of render layers.

    Repair action will change everything to match the asset frame range.

    This can be turned off by the artist to allow custom ranges.
    """

    label = "Validate Frame Range"
    order = openpype.api.ValidateContentsOrder
    families = ["animation",
                "pointcache",
                "camera",
                "renderlayer",
                "review",
                "yeticache"]
    optional = True
    actions = [openpype.api.RepairAction]

    def process(self, instance):
        context = instance.context
        if instance.data.get("tileRendering"):
            self.log.info((
                "Skipping frame range validation because "
                "tile rendering is enabled."
            ))
            return

        frame_start_handle = int(context.data.get("frameStartHandle"))
        frame_end_handle = int(context.data.get("frameEndHandle"))
        handles = int(context.data.get("handles"))
        handle_start = int(context.data.get("handleStart"))
        handle_end = int(context.data.get("handleEnd"))
        frame_start = int(context.data.get("frameStart"))
        frame_end = int(context.data.get("frameEnd"))

        inst_start = int(instance.data.get("frameStartHandle"))
        inst_end = int(instance.data.get("frameEndHandle"))

        # basic sanity checks
        assert frame_start_handle <= frame_end_handle, (
            "start frame is lower then end frame")

        assert handles >= 0, ("handles cannot have negative values")

        # compare with data on instance
        errors = []

        if(inst_start != frame_start_handle):
            errors.append("Instance start frame [ {} ] doesn't "
                          "match the one set on instance [ {} ]: "
                          "{}/{}/{}/{} (handle/start/end/handle)".format(
                              inst_start,
                              frame_start_handle,
                              handle_start, frame_start, frame_end, handle_end
                          ))

        if(inst_end != frame_end_handle):
            errors.append("Instance end frame [ {} ] doesn't "
                          "match the one set on instance [ {} ]: "
                          "{}/{}/{}/{} (handle/start/end/handle)".format(
                              inst_end,
                              frame_end_handle,
                              handle_start, frame_start, frame_end, handle_end
                          ))

        for e in errors:
            self.log.error(e)

        assert len(errors) == 0, ("Frame range settings are incorrect")

    @classmethod
    def repair(cls, instance):
        """
        Repair instance container to match asset data.
        """
        cmds.setAttr(
            "{}.frameStart".format(instance.data["name"]),
            instance.context.data.get("frameStartHandle"))

        cmds.setAttr(
            "{}.frameEnd".format(instance.data["name"]),
            instance.context.data.get("frameEndHandle"))
