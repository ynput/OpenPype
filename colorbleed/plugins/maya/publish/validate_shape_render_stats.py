import pyblish.api
import colorbleed.api

from maya import cmds


class ValidateShapeRenderStats(pyblish.api.Validator):
    """Ensure all render stats are set to the default values."""

    order = colorbleed.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['colorbleed.model']
    category = 'model'
    optional = False
    version = (0, 1, 0)
    label = 'Shape Default Render Stats'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.RepairAction]

    defaults = {'castsShadows': 1,
                'receiveShadows': 1,
                'motionBlur': 1,
                'primaryVisibility': 1,
                'smoothShading': 1,
                'visibleInReflections': 1,
                'visibleInRefractions': 1,
                'doubleSided': 1,
                'opposite': 0}

    @staticmethod
    def get_invalid(instance):
        # It seems the "surfaceShape" and those derived from it have
        # `renderStat` attributes.
        shapes = cmds.ls(instance, long=True, type='surfaceShape')
        invalid = []
        for shape in shapes:
            for attr, requiredValue in \
                    ValidateShapeRenderStats.defaults.iteritems():

                if cmds.attributeQuery(attr, node=shape, exists=True):
                    value = cmds.getAttr('{}.{}'.format(shape, attr))
                    if value != requiredValue:
                        invalid.append(shape)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Shapes with non-standard renderStats "
                             "found: {0}".format(invalid))

    @staticmethod
    def repair(instance):
        shape_render_defaults = ValidateShapeRenderStats.defaults
        for shape in ValidateShapeRenderStats.get_invalid(instance):
            for attr, default_value in shape_render_defaults.iteritems():

                if cmds.attributeQuery(attr, node=shape, exists=True):
                    plug = '{0}.{1}'.format(shape, attr)
                    value = cmds.getAttr(plug)
                    if value != default_value:
                        cmds.setAttr(plug, default_value)
