import pyblish.api
import pype.api

from maya import cmds

import pype.hosts.maya.action


class ValidateShapeRenderStats(pyblish.api.Validator):
    """Ensure all render stats are set to the default values."""

    order = pype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    label = 'Shape Default Render Stats'
    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.api.RepairAction]

    defaults = {'castsShadows': 1,
                'receiveShadows': 1,
                'motionBlur': 1,
                'primaryVisibility': 1,
                'smoothShading': 1,
                'visibleInReflections': 1,
                'visibleInRefractions': 1,
                'doubleSided': 1,
                'opposite': 0}

    @classmethod
    def get_invalid(cls, instance):
        # It seems the "surfaceShape" and those derived from it have
        # `renderStat` attributes.
        shapes = cmds.ls(instance, long=True, type='surfaceShape')
        invalid = []
        for shape in shapes:
            for attr, default_value in cls.defaults.iteritems():
                if cmds.attributeQuery(attr, node=shape, exists=True):
                    value = cmds.getAttr('{}.{}'.format(shape, attr))
                    if value != default_value:
                        invalid.append(shape)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Shapes with non-default renderStats "
                             "found: {0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        for shape in cls.get_invalid(instance):
            for attr, default_value in cls.defaults.iteritems():

                if cmds.attributeQuery(attr, node=shape, exists=True):
                    plug = '{0}.{1}'.format(shape, attr)
                    value = cmds.getAttr(plug)
                    if value != default_value:
                        cmds.setAttr(plug, default_value)
