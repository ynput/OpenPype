import pyblish.api

from maya import cmds
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError
)
from openpype.hosts.maya.api.lib_rendersetup import (
    get_attr_overrides,
    get_attr_in_layer,
)
from maya.app.renderSetup.model.override import AbsOverride


class ValidateFrameRange(pyblish.api.InstancePlugin):
    """Validates the frame ranges.

    This is an optional validator checking if the frame range on instance
    matches the frame range specified for the asset.

    It also validates render frame ranges of render layers.

    Repair action will change everything to match the asset frame range.

    This can be turned off by the artist to allow custom ranges.
    """

    label = "Validate Frame Range"
    order = ValidateContentsOrder
    families = ["animation",
                "pointcache",
                "camera",
                "proxyAbc",
                "renderlayer",
                "review",
                "yeticache"]
    optional = True
    actions = [RepairAction]
    exclude_families = []

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
        handle_start = int(context.data.get("handleStart"))
        handle_end = int(context.data.get("handleEnd"))
        frame_start = int(context.data.get("frameStart"))
        frame_end = int(context.data.get("frameEnd"))

        inst_start = int(instance.data.get("frameStartHandle"))
        inst_end = int(instance.data.get("frameEndHandle"))
        inst_frame_start = int(instance.data.get("frameStart"))
        inst_frame_end = int(instance.data.get("frameEnd"))
        inst_handle_start = int(instance.data.get("handleStart"))
        inst_handle_end = int(instance.data.get("handleEnd"))

        # basic sanity checks
        assert frame_start_handle <= frame_end_handle, (
            "start frame is lower then end frame")

        # compare with data on instance
        errors = []
        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return
        if (inst_start != frame_start_handle):
            errors.append("Instance start frame [ {} ] doesn't "
                          "match the one set on asset [ {} ]: "
                          "{}/{}/{}/{} (handle/start/end/handle)".format(
                              inst_start,
                              frame_start_handle,
                              handle_start, frame_start, frame_end, handle_end
                          ))

        if (inst_end != frame_end_handle):
            errors.append("Instance end frame [ {} ] doesn't "
                          "match the one set on asset [ {} ]: "
                          "{}/{}/{}/{} (handle/start/end/handle)".format(
                              inst_end,
                              frame_end_handle,
                              handle_start, frame_start, frame_end, handle_end
                          ))

        checks = {
            "frame start": (frame_start, inst_frame_start),
            "frame end": (frame_end, inst_frame_end),
            "handle start": (handle_start, inst_handle_start),
            "handle end": (handle_end, inst_handle_end)
        }
        for label, values in checks.items():
            if values[0] != values[1]:
                errors.append(
                    "{} on instance ({}) does not match with the asset "
                    "({}).".format(label.title(), values[1], values[0])
                )

        for e in errors:
            self.log.error(e)

        assert len(errors) == 0, ("Frame range settings are incorrect")

    @classmethod
    def repair(cls, instance):
        """
        Repair instance container to match asset data.
        """

        if "renderlayer" in instance.data.get("families"):
            # Special behavior for renderlayers
            cls.repair_renderlayer(instance)
            return

        node = instance.data["name"]
        context = instance.context

        frame_start_handle = int(context.data.get("frameStartHandle"))
        frame_end_handle = int(context.data.get("frameEndHandle"))
        handle_start = int(context.data.get("handleStart"))
        handle_end = int(context.data.get("handleEnd"))
        frame_start = int(context.data.get("frameStart"))
        frame_end = int(context.data.get("frameEnd"))

        # Start
        if cmds.attributeQuery("handleStart", node=node, exists=True):
            cmds.setAttr("{}.handleStart".format(node), handle_start)
            cmds.setAttr("{}.frameStart".format(node), frame_start)
        else:
            # Include start handle in frame start if no separate handleStart
            # attribute exists on the node
            cmds.setAttr("{}.frameStart".format(node), frame_start_handle)

        # End
        if cmds.attributeQuery("handleEnd", node=node, exists=True):
            cmds.setAttr("{}.handleEnd".format(node), handle_end)
            cmds.setAttr("{}.frameEnd".format(node), frame_end)
        else:
            # Include end handle in frame end if no separate handleEnd
            # attribute exists on the node
            cmds.setAttr("{}.frameEnd".format(node), frame_end_handle)

    @classmethod
    def repair_renderlayer(cls, instance):
        """Apply frame range in render settings"""

        layer = instance.data["setMembers"]
        context = instance.context

        start_attr = "defaultRenderGlobals.startFrame"
        end_attr = "defaultRenderGlobals.endFrame"

        frame_start_handle = int(context.data.get("frameStartHandle"))
        frame_end_handle = int(context.data.get("frameEndHandle"))

        cls._set_attr_in_layer(start_attr, layer, frame_start_handle)
        cls._set_attr_in_layer(end_attr, layer, frame_end_handle)

    @classmethod
    def _set_attr_in_layer(cls, node_attr, layer, value):

        if get_attr_in_layer(node_attr, layer=layer) == value:
            # Already ok. This can happen if you have multiple renderlayers
            # validated and there are no frame range overrides. The first
            # layer's repair would have fixed the global value already
            return

        overrides = list(get_attr_overrides(node_attr, layer=layer))
        if overrides:
            # We set the last absolute override if it is an absolute override
            # otherwise we'll add an Absolute override
            last_override = overrides[-1][1]
            if not isinstance(last_override, AbsOverride):
                collection = last_override.parent()
                node, attr = node_attr.split(".", 1)
                last_override = collection.createAbsoluteOverride(node, attr)

            cls.log.debug("Setting {attr} absolute override in "
                          "layer '{layer}': {value}".format(layer=layer,
                                                            attr=node_attr,
                                                            value=value))
            cmds.setAttr(last_override.name() + ".attrValue", value)

        else:
            # Set the attribute directly
            # (Note that this will set the global attribute)
            cls.log.debug("Setting global {attr}: {value}".format(
                attr=node_attr,
                value=value
            ))
            cmds.setAttr(node_attr, value)
