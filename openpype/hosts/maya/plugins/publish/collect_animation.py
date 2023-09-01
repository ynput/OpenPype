import pyblish.api

import maya.cmds as cmds


class CollectAnimationOutputGeometry(pyblish.api.InstancePlugin):
    """Collect out hierarchy data for instance.

    Collect all hierarchy nodes which reside in the out_SET of the animation
    instance or point cache instance. This is to unify the logic of retrieving
    that specific data. This eliminates the need to write two separate pieces
    of logic to fetch all hierarchy nodes.

    Results in a list of nodes from the content of the instances

    """

    order = pyblish.api.CollectorOrder + 0.4
    families = ["animation"]
    label = "Collect Animation Output Geometry"
    hosts = ["maya"]

    ignore_type = ["constraints"]

    def process(self, instance):
        """Collect the hierarchy nodes"""

        family = instance.data["family"]
        out_set = next((i for i in instance.data["setMembers"] if
                        i.endswith("out_SET")), None)

        if out_set is None:
            warning = "Expecting out_SET for instance of family '%s'" % family
            self.log.warning(warning)
            return

        members = cmds.ls(cmds.sets(out_set, query=True), long=True)

        # Get all the relatives of the members
        descendants = cmds.listRelatives(members,
                                         allDescendents=True,
                                         fullPath=True) or []
        descendants = cmds.ls(descendants, noIntermediate=True, long=True)

        # Add members and descendants together for a complete overview

        hierarchy = members + descendants

        # Ignore certain node types (e.g. constraints)
        ignore = cmds.ls(hierarchy, type=self.ignore_type, long=True)
        if ignore:
            ignore = set(ignore)
            hierarchy = [node for node in hierarchy if node not in ignore]

        # Store data in the instance for the validator
        instance.data["out_hierarchy"] = hierarchy

        if instance.data.get("farm"):
            instance.data["families"].append("publish.farm")

        # Alembic and Multiverse share the same attribute functionality but
        # different names.
        instance.data["writeNormals"] = (
            instance.data.get("writeNormals") or
            not instance.data.get("noNormals") or
            False
        )

        # Backwards compatibility for attributes.
        backwards_mapping = {
            "write_color_sets": "writeColorSets",
            "write_face_sets": "writeFaceSets",
            "include_parent_hierarchy": "includeParentHierarchy",
            "include_user_defined_attributes": "includeUserDefinedAttributes"
        }
        for key, value in backwards_mapping.items():
            if key in instance.data:
                instance.data[value] = instance.data[key]

        # Collect user defined attributes.
        if instance.data.get("includeUserDefinedAttributes", False):
            user_defined_attributes = set()
            for node in hierarchy:
                attrs = cmds.listAttr(node, userDefined=True) or list()
                user_defined_attributes.update(attrs)

            instance.data["userDefinedAttributes"] = list(
                user_defined_attributes
            )
