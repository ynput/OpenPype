from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateRigPointcacheShapeRenderStats(pyblish.api.Validator):
    """Ensure all render stats are set to the default values."""

    order = colorbleed.api.ValidateMeshOrder
    families = ['colorbleed.model']
    hosts = ['maya']
    category = 'model'
    optional = False
    version = (0, 1, 0)
    label = 'Rig Pointcache Shape Default Render Stats'
    actions = [colorbleed.api.SelectInvalidAction]

    defaults = {'castsShadows': 1,
                'receiveShadows': 1,
                'motionBlur': 1,
                'primaryVisibility': 1,
                'smoothShading': 1,
                'visibleInReflections': 1,
                'visibleInRefractions': 1,
                'doubleSided': 1,
                'opposite': 0}

    ignore_types = ("constraint",)

    @classmethod
    def get_pointcache_nodes(cls, instance):

        # Get out_SET
        sets = cmds.ls(instance, type='objectSet')
        pointcache_sets = [x for x in sets if x == 'out_SET']

        nodes = list()
        for s in pointcache_sets:
            members = cmds.sets(s, q=1)
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
        # It seems the "surfaceShape" and those derived from it have
        # `renderStat` attributes.

        nodes = cls.get_pointcache_nodes(instance)

        shapes = cmds.ls(nodes, long=True, type='surfaceShape')
        invalid = []
        for shape in shapes:
            for attr, requiredValue in \
                    ValidateRigPointcacheShapeRenderStats.defaults.iteritems():

                if cmds.attributeQuery(attr, node=shape, exists=True):
                    value = cmds.getAttr('{node}.{attr}'.format(node=shape,
                                                                attr=attr))
                    if value != requiredValue:
                        invalid.append(shape)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Shapes with non-standard renderStats "
                             "found: {0}".format(invalid))
