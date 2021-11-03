from typing import List

import mathutils

import pyblish.api
import openpype.hosts.blender.api.action


class ValidateCameraZeroKeyframe(pyblish.api.InstancePlugin):
    """Camera must have a keyframe at frame 0.

    Unreal shifts the first keyframe to frame 0. Forcing the camera to have
    a keyframe at frame 0 will ensure that the animation will be the same
    in Unreal and Blender.
    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["blender"]
    families = ["camera"]
    category = "geometry"
    version = (0, 1, 0)
    label = "Zero Keyframe"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]

    _identity = mathutils.Matrix()

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        for obj in [obj for obj in instance]:
            if obj.type == "CAMERA":
                if obj.animation_data and obj.animation_data.action:
                    action = obj.animation_data.action
                    frames_set = set()
                    for fcu in action.fcurves:
                        for kp in fcu.keyframe_points:
                            frames_set.add(kp.co[0])
                    frames = list(frames_set)
                    frames.sort()
                    if frames[0] != 0.0:
                        invalid.append(obj)
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Object found in instance is not in Object Mode: {invalid}")
