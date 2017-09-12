import maya.cmds as cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib
import avalon.io as io


class ValidateRigPointcacheRelatedNodeIds(pyblish.api.InstancePlugin):
    """Validate rig out_SET nodes have related ids to current context

    An ID is 'related' if its built in the current Item.

    Note that this doesn't ensure it's from the current Task. An ID created
    from `lookdev` has the same relation to the Item as one coming from others,
    like `rigging` or `modeling`.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.rigpointcache', 'colorbleed.pointcache']
    hosts = ['maya']
    label = 'Rig Pointcache Related Node Ids'
    actions = [colorbleed.api.SelectInvalidAction]
    optional = True

    ignore_types = ("constraint",)

    def process(self, instance):
        """Process all meshes"""

        print ">>>", instance.data

        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes found with non-related "
                               "asset IDs: {0}".format(invalid))

    @classmethod
    def get_pointcache_nodes(cls, instance):

        # Get out_SET
        sets = cmds.ls(instance, type='objectSet')
        pointcache_sets = [x for x in sets if x == 'out_SET']

        nodes = list()
        for s in pointcache_sets:
            members = cmds.sets(s, query=True)
            members = cmds.ls(members, long=True)  # ensure long names
            descendents = cmds.listRelatives(members,
                                             allDescendents=True,
                                             fullPath=True) or []
            descendents = cmds.ls(descendents,
                                  noIntermediate=True,
                                  long=True)
            hierarchy = members + descendents
            nodes.extend(hierarchy)

        # ignore certain node types (e.g. constraints)
        ignore = cmds.ls(nodes, type=cls.ignore_types, long=True)
        if ignore:
            ignore = set(ignore)
            nodes = [node for node in nodes if node not in ignore]

        return nodes

    @classmethod
    def get_invalid(cls, instance):
        invalid_items = []

        # get asset id
        nodes = cls.get_pointcache_nodes(instance)
        for node in nodes:
            node_id = lib.get_id(node)
            if not node_id:
                invalid_items.append(node)

        # Log invalid item ids
        if invalid_items:
            for item_id in sorted(invalid_items):
                cls.log.warning("Found invalid item id: {0}".format(item_id))

        return invalid_items

    @staticmethod
    def to_item(id):
        """Split the item id part from a node id"""
        return id.rsplit(":", 1)[0]
