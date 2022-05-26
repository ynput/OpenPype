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
