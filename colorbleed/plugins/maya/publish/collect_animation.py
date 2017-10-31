import pyblish.api

import maya.cmds as cmds


class CollectLook(pyblish.api.InstancePlugin):
    """Collect look data for instance.

    For the shapes/transforms of the referenced object to collect look for
    retrieve the user-defined attributes (like V-ray attributes) and their
    values as they were created in the current scene.

    For the members of the instance collect the sets (shadingEngines and
    other sets, e.g. VRayDisplacement) they are in along with the exact
    membership relations.

    Collects:
        lookAttribtutes (list): Nodes in instance with their altered attributes
        lookSetRelations (list): Sets and their memberships
        lookSets (list): List of set names included in the look

    """

    order = pyblish.api.CollectorOrder + 0.4
    families = ["colorbleed.animation", "colorbleed.pointcache"]
    label = "Collect Animation"
    hosts = ["maya"]

    ignore_type = ["constraints"]

    def process(self, instance):
        """Collect the Look in the instance with the correct layer settings"""

        family = instance.data["family"]
        if family == "colorbleed.animation":
            out_set = next((i for i in instance.data["setMembers"] if
                            i.endswith("out_SET")), None)

            assert out_set, ("Expecting out_SET for instance of family"
                             "'%s'" % family)
            members = cmds.ls(cmds.sets(out_set, query=True), long=True)
        else:
            members = cmds.ls(instance, long=True)

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

            return hierarchy

        # Store data in the instance for the validator
        instance.data["pointcache_data"] = hierarchy
