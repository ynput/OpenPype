from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateNoAnimation(pyblish.api.Validator):
    """Ensure no keyframes on nodes in the Instance.

    Even though a Model would extract without animCurves correctly this avoids
    getting different output from a model when extracted from a different
    frame than the first frame. (Might be overly restrictive though)

    """

    order = pype.api.ValidateContentsOrder
    label = "No Animation"
    hosts = ["maya"]
    families = ["model"]
    optional = True
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Keyframes found: {0}".format(invalid))

    @staticmethod
    def get_invalid(instance):

        nodes = instance[:]
        if not nodes:
            return []

        curves = cmds.keyframe(nodes, query=True, name=True)
        if curves:
            return list(set(cmds.listConnections(curves)))

        return []
