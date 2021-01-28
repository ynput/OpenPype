# -*- coding: utf-8 -*-
"""Plugin for validating naming conventions."""
from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateTransformNamingSuffix(pyblish.api.InstancePlugin):
    """Validates transform suffix based on the type of its children shapes.

    Suffices must be:
        - mesh:
            _GEO (regular geometry)
            _GES (geometry to be smoothed at render)
            _GEP (proxy geometry; usually not to be rendered)
            _OSD (open subdiv smooth at rendertime)
        - nurbsCurve: _CRV
        - nurbsSurface: _NRB
        - locator: _LOC
        - null/group: _GRP

    .. warning::
        This grabs the first child shape as a reference and doesn't use the
        others in the check.

    """

    order = pype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['model']
    category = 'cleanup'
    optional = True
    version = (0, 1, 0)
    label = 'Suffix Naming Conventions'
    actions = [pype.hosts.maya.action.SelectInvalidAction]
    SUFFIX_NAMING_TABLE = {'mesh': ["_GEO", "_GES", "_GEP", "_OSD"],
                           'nurbsCurve': ["_CRV"],
                           'nurbsSurface': ["_NRB"],
                           'locator': ["_LOC"],
                           None: ['_GRP']}

    ALLOW_IF_NOT_IN_SUFFIX_TABLE = True

    @staticmethod
    def is_valid_name(node_name, shape_type,
                      SUFFIX_NAMING_TABLE, ALLOW_IF_NOT_IN_SUFFIX_TABLE):
        """Return whether node's name is correct.

        The correctness for a transform's suffix is dependent on what
        `shape_type` it holds. E.g. a transform with a mesh might need and
        `_GEO` suffix.

        When `shape_type` is None the transform doesn't have any direct
        children shapes.

        Args:
            node_name (str): Node name.
            shape_type (str): Type of node.
            SUFFIX_NAMING_TABLE (dict): Mapping dict for suffixes.
            ALLOW_IF_NOT_IN_SUFFIX_TABLE (dict): Filter dict.

        """
        if shape_type not in SUFFIX_NAMING_TABLE:
            return ALLOW_IF_NOT_IN_SUFFIX_TABLE
        else:
            suffices = SUFFIX_NAMING_TABLE[shape_type]
            for suffix in suffices:
                if node_name.endswith(suffix):
                    return True
            return False

    @classmethod
    def get_invalid(cls, instance):
        """Get invalid nodes in instance.

        Args:
            instance (:class:`pyblish.api.Instance`): published instance.

        """
        transforms = cmds.ls(instance, type='transform', long=True)

        invalid = []
        for transform in transforms:
            shapes = cmds.listRelatives(transform,
                                        shapes=True,
                                        fullPath=True,
                                        noIntermediate=True)

            shape_type = cmds.nodeType(shapes[0]) if shapes else None
            if not cls.is_valid_name(transform, shape_type,
                                     cls.SUFFIX_NAMING_TABLE,
                                     cls.ALLOW_IF_NOT_IN_SUFFIX_TABLE):
                invalid.append(transform)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance.

        Args:
            instance (:class:`pyblish.api.Instance`): published instance.

        """
        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Incorrectly named geometry "
                             "transforms: {0}".format(invalid))
