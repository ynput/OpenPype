# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    RepairAction,
)

import hou


class AddDefaultPathAction(RepairAction):
    label = "Add a default path attribute"
    icon = "mdi.pencil-plus-outline"


class ValidatePrimitiveHierarchyPaths(pyblish.api.InstancePlugin):
    """Validate all primitives build hierarchy from attribute when enabled.

    The name of the attribute must exist on the prims and have the same name
    as Build Hierarchy from Attribute's `Path Attribute` value on the Alembic
    ROP node whenever Build Hierarchy from Attribute is enabled.

    """

    order = ValidateContentsOrder + 0.1
    families = ["pointcache"]
    hosts = ["houdini"]
    label = "Validate Prims Hierarchy Path"
    actions = [AddDefaultPathAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "See log for details. " "Invalid nodes: {0}".format(invalid),
                title=self.label
            )

    @classmethod
    def get_invalid(cls, instance):

        output_node = instance.data.get("output_node")
        rop_node = hou.node(instance.data["instance_node"])

        if output_node is None:
            cls.log.error(
                "SOP Output node in '%s' does not exist. "
                "Ensure a valid SOP output path is set." % rop_node.path()
            )

            return [rop_node]

        build_from_path = rop_node.parm("build_from_path").eval()
        if not build_from_path:
            cls.log.debug(
                "Alembic ROP has 'Build from Path' disabled. "
                "Validation is ignored.."
            )
            return

        path_attr = rop_node.parm("path_attrib").eval()
        if not path_attr:
            cls.log.error(
                "The Alembic ROP node has no Path Attribute"
                "value set, but 'Build Hierarchy from Attribute'"
                "is enabled."
            )
            return [rop_node]

        cls.log.debug("Checking for attribute: %s" % path_attr)

        # Check if the primitive attribute exists
        frame = instance.data.get("frameStart", 0)
        geo = output_node.geometryAtFrame(frame)

        # If there are no primitives on the current frame then we can't
        # check whether the path names are correct. So we'll just issue a
        # warning that the check can't be done consistently and skip
        # validation.
        if len(geo.iterPrims()) == 0:
            cls.log.warning(
                "No primitives found on current frame. Validation"
                " for primitive hierarchy paths will be skipped,"
                " thus can't be validated."
            )
            return

        # Check if there are any values for the primitives
        attrib = geo.findPrimAttrib(path_attr)
        if not attrib:
            cls.log.info(
                "Geometry Primitives are missing "
                "path attribute: `%s`" % path_attr
            )
            return [output_node]

        # Ensure at least a single string value is present
        if not attrib.strings():
            cls.log.info(
                "Primitive path attribute has no "
                "string values: %s" % path_attr
            )
            return [output_node]

        paths = geo.primStringAttribValues(path_attr)
        # Ensure all primitives are set to a valid path
        # Collect all invalid primitive numbers
        invalid_prims = [i for i, path in enumerate(paths) if not path]
        if invalid_prims:
            num_prims = len(geo.iterPrims())  # faster than len(geo.prims())
            cls.log.info(
                "Prims have no value for attribute `%s` "
                "(%s of %s prims)" % (path_attr, len(invalid_prims), num_prims)
            )
            return [output_node]

    @classmethod
    def repair(cls, instance):
        """Add a default path attribute Action.

        it's a helper action more than a repair action,
        which used to add a default single value.
        """

        rop_node = hou.node(instance.data["instance_node"])
        output_node = rop_node.parm('sop_path').evalAsNode()

        if not output_node:
            cls.log.debug(
                "Action isn't performed, empty SOP Path on %s"
                % rop_node
            )
            return

        # This check to prevent the action from running multiple times.
        # git_invalid only returns [output_node] when
        #   path attribute is the problem
        if cls.get_invalid(instance) != [output_node]:
            return

        path_attr = rop_node.parm("path_attrib").eval()

        path_node = output_node.parent().createNode("name", "AUTO_PATH")
        path_node.parm("attribname").set(path_attr)
        path_node.parm("name1").set('`opname("..")`/`opname("..")`Shape')

        cls.log.debug(
            "'%s' was created. It adds '%s' with a default single value"
            % (path_node, path_attr)
        )

        path_node.setGenericFlag(hou.nodeFlag.DisplayComment,True)
        path_node.setComment(
            'Auto path node created automatically by "Add a default path attribute"'
            '\nFeel free to modify or replace it.'
        )

        if output_node.type().name() in ['null', 'output']:
            # Connect before
            path_node.setFirstInput(output_node.input(0))
            path_node.moveToGoodPosition()
            output_node.setFirstInput(path_node)
            output_node.moveToGoodPosition()
        else:
            # Connect after
            path_node.setFirstInput(output_node)
            rop_node.parm('sop_path').set(path_node.path())
            path_node.moveToGoodPosition()

            cls.log.debug(
                "SOP path on '%s' updated to new output node '%s'"
                % (rop_node, path_node)
            )
