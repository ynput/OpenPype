from collections import defaultdict

import pyblish.api
import colorbleed.api


class ValidateRigPointcacheNodeIds(pyblish.api.InstancePlugin):
    """Validate rig out_SET nodes have ids

    The nodes in a rig's out_SET must all have node IDs
    that are all unique.

    Geometry in a rig should be using published model's geometry.
    As such when this validation doesn't pass it means you're using
    local newly created nodes that are not coming from a published
    model file. Ensure you update the ids from the model.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.rig', "colorbleed.rigpointcache"]
    hosts = ['maya']
    label = 'Rig Pointcache Node Ids'
    actions = [colorbleed.api.SelectInvalidAction]

    ignore_types = ("constraint",)

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

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
            descendents = cmds.ls(descendents, noIntermediate=True, long=True)
            hierarchy = members + descendents
            nodes.extend(hierarchy)

        # ignore certain node types (e.g. constraints)
        ignore = cmds.ls(nodes, type=cls.ignore_types, long=True)
        if ignore:
            ignore = set(ignore)
            nodes = [node for node in nodes if node not in ignore]

        # Missing ids
        missing = list()
        ids = defaultdict(list)
        for node in nodes:
            has_id = cmds.attributeQuery("mbId", node=node, exists=True)
            if not has_id:
                missing.append(node)
                continue

            uuid = cmds.getAttr("{}.mbId".format(node))
            ids[uuid].append(node)

        non_uniques = list()
        for uuid, nodes in ids.iteritems():
            if len(nodes) > 1:
                non_uniques.extend(nodes)

        if missing:
            cls.log.warning("Missing node ids: {0}".format(missing))

        if non_uniques:
            cls.log.warning("Non unique node ids: {0}".format(non_uniques))

        invalid = missing + non_uniques
        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Missing or non-unique node IDs: "
                               "{0}".format(invalid))
