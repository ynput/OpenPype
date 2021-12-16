from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib


class ValidateModelContent(pyblish.api.InstancePlugin):
    """Adheres to the content of 'model' family

    - Must have one top group. (configurable)
    - Must only contain: transforms, meshes and groups

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Model Content"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    validate_top_group = True

    @classmethod
    def get_invalid(cls, instance):

        content_instance = instance.data.get("setMembers", None)
        if not content_instance:
            cls.log.error("Instance has no nodes!")
            return True

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
        assemblies = cmds.ls(content_instance, assemblies=True, long=True)
        if len(assemblies) != 1 and cls.validate_top_group:
            cls.log.error("Must have exactly one top group")
            return assemblies
        if len(assemblies) == 0:
            cls.log.warning("No top group found. "
                            "(Are there objects in the instance?"
                            " Or is it parented in another group?)")
            return assemblies or True

        def _is_visible(node):
            """Return whether node is visible"""
            return lib.is_visible(node,
                                  displayLayer=False,
                                  intermediateObject=True,
                                  parentHidden=True,
                                  visibility=True)

        # The roots must be visible (the assemblies)
        for assembly in assemblies:
            if not _is_visible(assembly):
                cls.log.error("Invisible assembly (root node) is not "
                              "allowed: {0}".format(assembly))
                invalid.add(assembly)

        # Ensure at least one shape is visible
        if not any(_is_visible(shape) for shape in shapes):
            cls.log.error("No visible shapes in the model instance")
            invalid.update(shapes)

        return list(invalid)

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Model content is invalid. See log.")
