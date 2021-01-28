from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateTransformZero(pyblish.api.Validator):
    """Transforms can't have any values

    To solve this issue, try freezing the transforms. So long
    as the transforms, rotation and scale values are zero,
    you're all good.

    """

    order = pype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    category = "geometry"
    version = (0, 1, 0)
    label = "Transform Zero (Freeze)"
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    _identity = [1.0, 0.0, 0.0, 0.0,
                 0.0, 1.0, 0.0, 0.0,
                 0.0, 0.0, 1.0, 0.0,
                 0.0, 0.0, 0.0, 1.0]
    _tolerance = 1e-30

    @classmethod
    def get_invalid(cls, instance):
        """Returns the invalid transforms in the instance.

        This is the same as checking:
        - translate == [0, 0, 0] and rotate == [0, 0, 0] and
          scale == [1, 1, 1] and shear == [0, 0, 0]

        .. note::
            This will also catch camera transforms if those
            are in the instances.

        Returns:
            list: Transforms that are not identity matrix

        """

        transforms = cmds.ls(instance, type="transform")

        invalid = []
        for transform in transforms:
            if ('_LOC' in transform) or ('_loc' in transform):
                continue
            mat = cmds.xform(transform, q=1, matrix=True, objectSpace=True)
            if not all(abs(x-y) < cls._tolerance
                       for x, y in zip(cls._identity, mat)):
                invalid.append(transform)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Nodes found with transform "
                             "values: {0}".format(invalid))
