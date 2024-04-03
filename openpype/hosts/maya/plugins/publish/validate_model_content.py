from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateModelContent(pyblish.api.InstancePlugin,
                           OptionalPyblishPluginMixin):
    """Adheres to the content of 'model' product type

    - Must have one top group. (configurable)
    - Must only contain: transforms, meshes and groups

    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Model Content"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    validate_top_group = True
    optional = False

    @classmethod
    def get_invalid(cls, instance):

        content_instance = instance.data.get("setMembers", None)
        if not content_instance:
            cls.log.error("Instance has no nodes!")
            return [instance.data["name"]]

        # All children will be included in the extracted export so we also
        # validate *all* descendents of the set members and we skip any
        # intermediate shapes
        descendants = cmds.listRelatives(content_instance,
                                         allDescendents=True,
                                         fullPath=True) or []
        descendants = cmds.ls(descendants, noIntermediate=True, long=True)
        content_instance = list(set(content_instance + descendants))

        # Ensure only valid node types
        allowed = ('mesh', 'transform', 'nurbsCurve', 'nurbsSurface', 'locator')
        nodes = cmds.ls(content_instance, long=True)
        valid = cmds.ls(content_instance, long=True, type=allowed)
        invalid = set(nodes) - set(valid)

        if invalid:
            cls.log.error("These nodes are not allowed: %s" % invalid)
            return list(invalid)

        if not valid:
            cls.log.error("No valid nodes in the instance")
            return True

        # Ensure it has shapes
        shapes = cmds.ls(valid, long=True, shapes=True)
        if not shapes:
            cls.log.error("No shapes in the model instance")
            return True

        # Top group
        top_parents = set([x.split("|")[1] for x in content_instance])
        if cls.validate_top_group and len(top_parents) != 1:
            cls.log.error("Must have exactly one top group")
            return top_parents

        def _is_visible(node):
            """Return whether node is visible"""
            return lib.is_visible(node,
                                  displayLayer=False,
                                  intermediateObject=True,
                                  parentHidden=True,
                                  visibility=True)

        # The roots must be visible (the assemblies)
        for parent in top_parents:
            if not _is_visible(parent):
                cls.log.error("Invisible parent (root node) is not "
                              "allowed: {0}".format(parent))
                invalid.add(parent)

        # Ensure at least one shape is visible
        if not any(_is_visible(shape) for shape in shapes):
            cls.log.error("No visible shapes in the model instance")
            invalid.update(shapes)

        return list(invalid)

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                title="Model content is invalid",
                message="See log for more details"
            )
