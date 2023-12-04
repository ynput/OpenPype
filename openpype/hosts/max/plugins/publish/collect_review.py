# dont forget getting the focal length for burnin
"""Collect Review"""
import pyblish.api

from pymxs import runtime as rt
from openpype.lib import BoolDef
from openpype.hosts.max.api.lib import get_max_version
from openpype.pipeline.publish import (
    OpenPypePyblishPluginMixin,
    KnownPublishError
)


class CollectReview(pyblish.api.InstancePlugin,
                    OpenPypePyblishPluginMixin):
    """Collect Review Data for Preview Animation"""

    order = pyblish.api.CollectorOrder + 0.02
    label = "Collect Review Data"
    hosts = ['max']
    families = ["review"]

    def process(self, instance):
        nodes = instance.data["members"]

        def is_camera(node):
            is_camera_class = rt.classOf(node) in rt.Camera.classes
            return is_camera_class and rt.isProperty(node, "fov")

        # Use first camera in instance
        cameras = [node for node in nodes if is_camera(node)]
        if cameras:
            if len(cameras) > 1:
                self.log.warning(
                    "Found more than one camera in instance, using first "
                    f"one found: {cameras[0]}"
                )
            camera = cameras[0]
            camera_name = camera.name
            focal_length = camera.fov
        else:
            raise KnownPublishError(
                "Unable to find a valid camera in 'Review' container."
                " Only native max Camera supported. "
                f"Found objects: {nodes}"
            )
        creator_attrs = instance.data["creator_attributes"]
        attr_values = self.get_attr_values_from_data(instance.data)

        general_preview_data = {
            "review_camera": camera_name,
            "frameStart": instance.data["frameStartHandle"],
            "frameEnd": instance.data["frameEndHandle"],
            "percentSize": creator_attrs["percentSize"],
            "imageFormat": creator_attrs["imageFormat"],
            "keepImages": creator_attrs["keepImages"],
            "fps": instance.context.data["fps"],
            "review_width": creator_attrs["review_width"],
            "review_height": creator_attrs["review_height"],
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

            preview_data = {
                "vpStyle": creator_attrs["visualStyleMode"],
                "vpPreset": creator_attrs["viewportPreset"],
                "vpTextures": creator_attrs["vpTexture"],
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
        else:
            general_viewport = {
                "dspBkg": attr_values.get("dspBkg"),
                "dspGrid": attr_values.get("dspGrid")
            }
            nitrous_manager = {
                "AntialiasingQuality": creator_attrs["antialiasingQuality"],
            }
            nitrous_viewport = {
                "VisualStyleMode": creator_attrs["visualStyleMode"],
                "ViewportPreset": creator_attrs["viewportPreset"],
                "UseTextureEnabled": creator_attrs["vpTexture"]
            }
            preview_data = {
                "general_viewport": general_viewport,
                "nitrous_manager": nitrous_manager,
                "nitrous_viewport": nitrous_viewport,
                "vp_btn_mgr": {"EnableButtons": False}
            }

        # Enable ftrack functionality
        instance.data.setdefault("families", []).append('ftrack')

        burnin_members = instance.data.setdefault("burninDataMembers", {})
        burnin_members["focalLength"] = focal_length

        instance.data.update(general_preview_data)
        instance.data["viewport_options"] = preview_data

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
