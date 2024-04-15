import pyblish.api

from openpype.hosts.maya.api.lib import iter_visible_nodes_in_range
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateAlembicVisibleOnly(pyblish.api.InstancePlugin,
                                 OptionalPyblishPluginMixin):
    """Validates at least a single node is visible in frame range.

    This validation only validates if the `visibleOnly` flag is enabled
    on the instance - otherwise the validation is skipped.

    """
    order = ValidateContentsOrder + 0.05
    label = "Alembic Visible Only"
    hosts = ["maya"]
    families = ["pointcache", "animation"]
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        if not instance.data.get("visibleOnly", False):
            self.log.debug("Visible only is disabled. Validation skipped..")
            return

        invalid = self.get_invalid(instance)
        if invalid:
            start, end = self.get_frame_range(instance)
            raise PublishValidationError("No visible nodes found in "
                               "frame range {}-{}.".format(start, end))

    @classmethod
    def get_invalid(cls, instance):

        if instance.data["family"] == "animation":
            # Special behavior to use the nodes in out_SET
            nodes = instance.data["out_hierarchy"]
        else:
            nodes = instance[:]

        start, end = cls.get_frame_range(instance)
        if not any(iter_visible_nodes_in_range(nodes, start, end)):
            # Return the nodes we have considered so the user can identify
            # them with the select invalid action
            return nodes

    @staticmethod
    def get_frame_range(instance):
        data = instance.data
        return data["frameStartHandle"], data["frameEndHandle"]
