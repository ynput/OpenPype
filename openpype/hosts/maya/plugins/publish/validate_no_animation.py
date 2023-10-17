from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    OptionalPyblishPluginMixin,
    PublishValidationError
)


def _as_report_list(values, prefix="- ", suffix="\n"):
    """Return list as bullet point list for a report"""
    if not values:
        return ""
    return prefix + (suffix + prefix).join(values)


class ValidateNoAnimation(pyblish.api.Validator,
                          OptionalPyblishPluginMixin):
    """Ensure no keyframes on nodes in the Instance.

    Even though a Model would extract without animCurves correctly this avoids
    getting different output from a model when extracted from a different
    frame than the first frame. (Might be overly restrictive though)

    """

    order = ValidateContentsOrder
    label = "No Animation"
    hosts = ["maya"]
    families = ["model"]
    optional = True
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Keyframes found on:\n\n{0}".format(
                    _as_report_list(sorted(invalid))
                ),
                title="Keyframes on model"
            )

    @staticmethod
    def get_invalid(instance):

        nodes = instance[:]
        if not nodes:
            return []

        curves = cmds.keyframe(nodes, query=True, name=True)
        if curves:
            return list(set(cmds.listConnections(curves)))

        return []
