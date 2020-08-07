import pyblish.api
import pype.api
from pype.hosts.maya import lib

from maya import cmds


class ValidateVRayDistributedRendering(pyblish.api.InstancePlugin):
    """Validate V-Ray Distributed Rendering is ignored in batch mode.

    Whenever Distributed Rendering is enabled for V-Ray in the render settings
    ensure that the "Ignore in batch mode" is enabled so the submitted job
    won't try to render each frame with all machines resulting in faulty
    errors.

    """

    order = pype.api.ValidateContentsOrder
    label = "VRay Distributed Rendering"
    families = ["renderlayer"]
    actions = [pype.api.RepairAction]

    # V-Ray attribute names
    enabled_attr = "vraySettings.sys_distributed_rendering_on"
    ignored_attr = "vraySettings.sys_distributed_rendering_ignore_batch"

    def process(self, instance):

        if instance.data.get("renderer") != "vray":
            # If not V-Ray ignore..
            return

        vray_settings = cmds.ls("vraySettings", type="VRaySettingsNode")
        assert vray_settings, "Please ensure a VRay Settings Node is present"

        renderlayer = instance.data['setMembers']

        if not lib.get_attr_in_layer(self.enabled_attr, layer=renderlayer):
            # If not distributed rendering enabled, ignore..
            return

        # If distributed rendering is enabled but it is *not* set to ignore
        # during batch mode we invalidate the instance
        if not lib.get_attr_in_layer(self.ignored_attr, layer=renderlayer):
            raise RuntimeError("Renderlayer has distributed rendering enabled "
                               "but is not set to ignore in batch mode.")

    @classmethod
    def repair(cls, instance):

        renderlayer = instance.data.get("setMembers")
        with lib.renderlayer(renderlayer):
            cls.log.info("Enabling Distributed Rendering "
                         "ignore in batch mode..")
            cmds.setAttr(cls.ignored_attr, True)
