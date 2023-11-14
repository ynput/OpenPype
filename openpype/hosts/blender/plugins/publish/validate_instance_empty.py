import pyblish.api
from openpype.pipeline.publish import PublishValidationError


class ValidateInstanceEmpty(pyblish.api.InstancePlugin):
    """Validator to verify that the instance is not empty"""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["model", "pointcache", "rig", "camera" "layout", "blendScene"]
    label = "Validate Instance is not Empty"
    optional = False

    def process(self, instance):
        # Members are collected by `collect_instance` so we only need to check
        # whether any member is included. The instance node will be included
        # as a member as well, hence we will check for at least 2 members
        if len(instance) < 2:
            raise PublishValidationError(f"Instance {instance.name} is empty.")
