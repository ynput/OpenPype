import maya.cmds as cmds

import pyblish.api
import colorbleed.api

from cb.utils.maya.core import getHighestInHierarchy, iterParents

_IDENTITY = [1.0, 0.0, 0.0, 0.0,
             0.0, 1.0, 0.0, 0.0,
             0.0, 0.0, 1.0, 0.0,
             0.0, 0.0, 0.0, 1.0]

_ATTRS = ['tx', 'ty', 'tz',
          'rx', 'ry', 'rz',
          'sx', 'sy', 'sz',
          'shearXY', 'shearXZ', 'shearYZ']


def is_identity(node, tolerance=1e-30):
    mat = cmds.xform(node, query=True, matrix=True, objectSpace=True)
    if not all(abs(x - y) < tolerance for x, y in zip(_IDENTITY, mat)):
        return False
    return True


def is_animated(node):
    return any(cmds.listConnections("{}.{}".format(node, attr), source=True,
                                    destination=False) for attr in _ATTRS)


class ValidateLayoutParentNoTransforms(pyblish.api.InstancePlugin):
    """Validate layout parents have no transformations.

    The parent nodes above the extracted layout contents MUST have zero
    transformation (no offsets in translate, rotate, scale) for this pass
    validly.

    This is required to ensure no offsets are lacking from extracted caches.

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.layout']
    hosts = ['maya']
    label = 'Layout No Parent Transforms'
    actions = [colorbleed.api.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        invalid = []

        # Get highest in hierarchy
        nodes = instance.data["setMembers"]
        highest = getHighestInHierarchy(nodes)

        for node in highest:
            for parent in iterParents(node):
                if not is_identity(parent) or is_animated(parent):
                    invalid.append(parent)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Transforms (non-referenced) found in layout "
                               "without asset IDs: {0}".format(invalid))
