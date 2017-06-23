import maya.cmds as cmds

import pyblish.api
import colorbleed.api

import cbra.utils.maya.node_uuid as id_utils


class ValidateRigPointcacheRelatedNodeIds(pyblish.api.InstancePlugin):
    """Validate rig pointcache_SET nodes have related ids to current context

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

    @classmethod
    def get_pointcache_nodes(cls, instance):

        # Get pointcache_SET
        sets = cmds.ls(instance, type='objectSet')
        pointcache_sets = [x for x in sets if x == 'pointcache_SET']

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
        import cbra.lib

        # Get a full context from the instance context
        context = instance.data['instanceContext']
        item_path = context['itemPath']
        context = cbra.lib.parse_context(item_path)
        nodes = cls.get_pointcache_nodes(instance)

        def to_item(id):
            """Split the item id part from a node id"""
            return id.rsplit(":", 1)[0]

        # Generate a fake id in the current context to retrieve the item
        # id prefix that should match with ids on the nodes
        fake_node = "__node__"
        ids = id_utils.generate_ids(context, [fake_node])
        id = ids[fake_node]
        item_prefix = to_item(id)

        # Parse the invalid
        invalid = list()
        invalid_items = set()
        for member in nodes:
            member_id = id_utils.get_id(member)

            # skip nodes without ids
            if not member_id:
                continue

            if not member_id.startswith(item_prefix):
                invalid.append(member)
                invalid_items.add(to_item(member_id))

        # Log invalid item ids
        if invalid_items:
            for item_id in sorted(invalid_items):
                cls.log.warning("Found invalid item id: {0}".format(item_id))

        return invalid

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Nodes found with non-related "
                               "asset IDs: {0}".format(invalid))

