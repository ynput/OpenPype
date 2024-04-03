from maya import cmds

import pyblish.api

import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateTransformZero(pyblish.api.Validator,
                            OptionalPyblishPluginMixin):
    """Transforms can't have any values

    To solve this issue, try freezing the transforms. So long
    as the transforms, rotation and scale values are zero,
    you're all good.

    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Transform Zero (Freeze)"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    _identity = [1.0, 0.0, 0.0, 0.0,
                 0.0, 1.0, 0.0, 0.0,
                 0.0, 0.0, 1.0, 0.0,
                 0.0, 0.0, 0.0, 1.0]
    _tolerance = 1e-30
    optional = True

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
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:

            names = "<br>".join(
                " - {}".format(node) for node in invalid
            )

            raise PublishValidationError(
                title="Transform Zero",
                message="The model publish allows no transformations. You must"
                        " <b>freeze transformations</b> to continue.<br><br>"
                        "Nodes found with transform values: "
                        "{0}".format(names))
