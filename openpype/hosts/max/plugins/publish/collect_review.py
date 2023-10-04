# dont forget getting the focal length for burnin
"""Collect Review"""
import pyblish.api

from pymxs import runtime as rt
from openpype.lib import BoolDef
from openpype.hosts.max.api.lib import get_max_version
from openpype.pipeline.publish import OpenPypePyblishPluginMixin


class CollectReview(pyblish.api.InstancePlugin,
                    OpenPypePyblishPluginMixin):
    """Collect Review Data for Preview Animation"""

    order = pyblish.api.CollectorOrder + 0.02
    label = "Collect Review Data"
    hosts = ['max']
    families = ["review"]

    def process(self, instance):
        nodes = instance.data["members"]
        focal_length = None
        camera_name = None
        for node in nodes:
            if rt.classOf(node) in rt.Camera.classes:
                camera_name = node.name
                focal_length = node.fov

        attr_values = self.get_attr_values_from_data(instance.data)
        data = {
            "review_camera": camera_name,
            "frameStart": instance.context.data["frameStart"],
            "frameEnd": instance.context.data["frameEnd"],
            "fps": instance.context.data["fps"],
            "dspGeometry": attr_values.get("dspGeometry"),
            "dspShapes": attr_values.get("dspShapes"),
            "dspLights": attr_values.get("dspLights"),
            "dspCameras": attr_values.get("dspCameras"),
            "dspHelpers": attr_values.get("dspHelpers"),
            "dspParticles": attr_values.get("dspParticles"),
            "dspBones": attr_values.get("dspBones"),
            "dspBkg": attr_values.get("dspBkg"),
            "dspGrid": attr_values.get("dspGrid"),
            "dspSafeFrame": attr_values.get("dspSafeFrame"),
            "dspFrameNums": attr_values.get("dspFrameNums")
        }

        if int(get_max_version()) >= 2024:
            colorspace_mgr = rt.ColorPipelineMgr      # noqa
            display = next(
                (display for display in colorspace_mgr.GetDisplayList()))
            view_transform = next(
                (view for view in colorspace_mgr.GetViewList(display)))
            instance.data["colorspaceConfig"] = colorspace_mgr.OCIOConfigPath
            instance.data["colorspaceDisplay"] = display
            instance.data["colorspaceView"] = view_transform

        # Enable ftrack functionality
        instance.data.setdefault("families", []).append('ftrack')

        burnin_members = instance.data.setdefault("burninDataMembers", {})
        burnin_members["focalLength"] = focal_length

        self.log.debug(f"data:{data}")
        instance.data.update(data)

    @classmethod
    def get_attribute_defs(cls):
        return [
            BoolDef("dspGeometry",
                    label="Geometry",
                    default=True),
            BoolDef("dspShapes",
                    label="Shapes",
                    default=False),
            BoolDef("dspLights",
                    label="Lights",
                    default=False),
            BoolDef("dspCameras",
                    label="Cameras",
                    default=False),
            BoolDef("dspHelpers",
                    label="Helpers",
                    default=False),
            BoolDef("dspParticles",
                    label="Particle Systems",
                    default=True),
            BoolDef("dspBones",
                    label="Bone Objects",
                    default=False),
            BoolDef("dspBkg",
                    label="Background",
                    default=True),
            BoolDef("dspGrid",
                    label="Active Grid",
                    default=False),
            BoolDef("dspSafeFrame",
                    label="Safe Frames",
                    default=False),
            BoolDef("dspFrameNums",
                    label="Frame Numbers",
                    default=False)
        ]
