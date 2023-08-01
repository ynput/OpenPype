# -*- coding: utf-8 -*-
"""It's almost the same as
'validate_primitive_hierarchy_paths.py'
however this one includes more comments for demonstration.

FYI, path for fbx behaves a little differently.
In maya terms:
in Filmbox FBX: it sets the name of the object
in Alembic ROP: it sets the name of the shape
"""

import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    RepairAction,
)
from openpype.hosts.houdini.api.action import (
    SelectInvalidAction,
    SelectROPAction,
)

import hou

# Each validation can have a single repair action
# which calls the repair method
class AddDefaultPathAction(RepairAction):
    label = "Add a default path"
    icon = "mdi.pencil-plus-outline"


class ValidatePrimitiveHierarchyPaths(pyblish.api.InstancePlugin):
    """Validate all primitives build hierarchy from attribute
    when enabled.

    The name of the attribute must exist on the prims and have the
    same name as Build Hierarchy from Attribute's `Path Attribute`
    value on the FilmBox node.
    This validation enables 'Build Hierarchy from Attribute'
    by default.
    """

    # Usually you will this value by default
    order = ValidateContentsOrder + 0.1
    families = ["filmboxfbx"]
    hosts = ["houdini"]
    label = "Validate FBX Hierarchy Path"

    # Validation can have as many actions as you want
    # all of these actions are defined in a seperate place
    # unlike the repair action
    actions = [SelectInvalidAction, AddDefaultPathAction,
               SelectROPAction]

    # overrides InstancePlugin.process()
    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            nodes = [n.name() for n in invalid]
            raise PublishValidationError(
                "See log for details. "
                "Invalid nodes: {0}".format(nodes),
                title=self.label
            )

    # This method was named get_invalid as a convention
    # it's also used by SelectInvalidAction to select
    # the returned node
    @classmethod
    def get_invalid(cls, instance):

        output_node = instance.data.get("output_node")
        rop_node = hou.node(instance.data["instance_node"])

        if output_node is None:
            cls.log.error(
                "SOP Output node in '%s' does not exist. "
                "Ensure a valid SOP output path is set.",
                rop_node.path()
            )

            return [rop_node]

        build_from_path = rop_node.parm("buildfrompath").eval()
        if not build_from_path:
            cls.log.debug(
                "Filmbox FBX has 'Build from Path' disabled. "
                "Enbaling it as default."
            )
            rop_node.parm("buildfrompath").set(1)

        path_attr = rop_node.parm("pathattrib").eval()
        if not path_attr:
            cls.log.debug(
                "Filmbox FBX node has no Path Attribute"
                "value set, setting it to 'path' as default."
            )
            rop_node.parm("pathattrib").set("path")

        cls.log.debug("Checking for attribute: %s", path_attr)

        if not hasattr(output_node, "geometry"):
            # In the case someone has explicitly set an Object
            # node instead of a SOP node in Geometry context
            # then for now we ignore - this allows us to also
            # export object transforms.
            cls.log.warning("No geometry output node found,"
                            " skipping check..")
            return

        # Check if the primitive attribute exists
        frame = instance.data.get("frameStart", 0)
        geo = output_node.geometryAtFrame(frame)

        # If there are no primitives on the current frame then
        # we can't check whether the path names are correct.
        # So we'll just issue a warning that the check can't
        # be done consistently and skip validation.

        if len(geo.iterPrims()) == 0:
            cls.log.warning(
                "No primitives found on current frame."
                " Validation for primitive hierarchy"
                " paths will be skipped,"
                " thus can't be validated."
            )
            return

        # Check if there are any values for the primitives
        attrib = geo.findPrimAttrib(path_attr)
        if not attrib:
            cls.log.info(
                "Geometry Primitives are missing "
                "path attribute: `%s`", path_attr
            )
            return [output_node]

        # Ensure at least a single string value is present
        if not attrib.strings():
            cls.log.info(
                "Primitive path attribute has no "
                "string values: %s", path_attr
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
                "(%s of %s prims)",
                path_attr, len(invalid_prims), num_prims
            )
            return [output_node]

    # what repair action expects to find and call
    @classmethod
    def repair(cls, instance):
        """Add a default path attribute Action.

        It is a helper action more than a repair action,
        used to add a default single value for the path.
        """

        rop_node = hou.node(instance.data["instance_node"])
        # I'm doing so because an artist may change output node
        # before clicking the button.
        output_node = rop_node.parm("startnode").evalAsNode()

        if not output_node:
            cls.log.debug(
                "Action isn't performed, invalid SOP Path on %s",
                rop_node
            )
            return

        # This check to prevent the action from running multiple times.
        # git_invalid only returns [output_node] when
        #   path attribute is the problem
        if cls.get_invalid(instance) != [output_node]:
            return

        path_attr = rop_node.parm("pathattrib").eval()

        path_node = output_node.parent().createNode("name",
                                                    "AUTO_PATH")
        path_node.parm("attribname").set(path_attr)
        path_node.parm("name1").set('`opname("..")`_GEO')

        cls.log.debug(
            "'%s' was created. It adds '%s' with a default"
            " single value", path_node, path_attr
        )

        path_node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
        path_node.setComment(
            'Auto path node was created automatically by '
            '"Add a default path attribute"'
            '\nFeel free to modify or replace it.'
        )

        if output_node.type().name() in ["null", "output"]:
            # Connect before
            path_node.setFirstInput(output_node.input(0))
            path_node.moveToGoodPosition()
            output_node.setFirstInput(path_node)
            output_node.moveToGoodPosition()
        else:
            # Connect after
            path_node.setFirstInput(output_node)
            rop_node.parm("startnode").set(path_node.path())
            path_node.moveToGoodPosition()

            cls.log.debug(
                "SOP path on '%s' updated to new output node '%s'",
                rop_node, path_node
            )
