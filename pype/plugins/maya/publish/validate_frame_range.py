import pyblish.api
import pype.api

from maya import cmds


class ValidateFrameRange(pyblish.api.InstancePlugin):
    """Valides the frame ranges.

    This is optional validator checking if the frame range on instance
    matches the one of asset. It also validate render frame range of render
    layers

    Repair action will change everything to match asset.

    This can be turned off by artist to allow custom ranges.
    """

    label = "Validate Frame Range"
    order = pype.api.ValidateContentsOrder
    families = ["animation",
                "pointcache",
                "camera",
                "renderlayer",
                "review",
                "yeticache"]
    optional = True
    actions = [pype.api.RepairAction]

    def process(self, instance):
        context = instance.context

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

        if "renderlayer" in self.families:

            render_start = int(cmds.getAttr("defaultRenderGlobals.startFrame"))
            render_end = int(cmds.getAttr("defaultRenderGlobals.endFrame"))

            if int(render_start) != inst_start:
                errors.append("Render settings start frame is set to [ {} ] "
                              "and doesn't match the one set on "
                              "asset [ {} ]: "
                              "{}/{}/{}/{} (handle/start/end/handle)".format(
                                  int(render_start),
                                  frame_start_handle,
                                  handle_start, frame_start, frame_end,
                                  handle_end
                              ))

            if int(render_end) != inst_end:
                errors.append("Render settings end frame is set to [ {} ] "
                              "and doesn't match the one set on "
                              "asset [ {} ]: "
                              "{}/{}/{}/{} (handle/start/end/handle)".format(
                                  int(render_end),
                                  frame_end_handle,
                                  handle_start, frame_start, frame_end,
                                  handle_end
                              ))

        for e in errors:
            self.log.error(e)

        assert len(errors) == 0, ("Frame range settings are incorrect")

    @classmethod
    def repair(cls, instance):
        """
        Repair by calling avalon reset frame range function. This will set
        timeline frame range, render settings range and frame information
        on instance container to match asset data.
        """
        import avalon.maya.interactive
        avalon.maya.interactive.reset_frame_range()
        cmds.setAttr(
            "{}.frameStart".format(instance.data["name"]),
            instance.context.data.get("frameStartHandle"))

        cmds.setAttr(
            "{}.frameEnd".format(instance.data["name"]),
            instance.context.data.get("frameEndHandle"))
