from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateSingleShader(pyblish.api.InstancePlugin):
    """Validate default shaders in the scene have their default connections.

    For example the lambert1 could potentially be disconnected from the
    initialShadingGroup. As such it's not lambert1 that will be identified
    as the default shader which can have unpredictable results.

    To fix the default connections need to be made again. See the logs for
    more details on which connections are missing.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look Single Shader Per Shape'

    # The default connections to check
    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found shapes which have multiple "
                               "shadingEngines connected."
                               "\n{}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        shape_types = ["numrbsCurve", "nurbsSurface", "mesh"]

        # Get all shapes from the instance
        shapes = set()
        for node in instance[:]:

            nodetype = cmds.nodeType(node)
            if nodetype in shape_types:
                shapes.add(node)

            elif nodetype == "transform":
                shape = cmds.listRelatives(node, children=True,
                                           type="shape", fullPath=True)
                if not shape:
                    continue
                shapes.add(shape[0])

        # Check the number of connected shadingEngines per shape
        for shape in shapes:
            shading_engines = cmds.listConnections(shape,
                                                   destination=True,
                                                   type="shadingEngine") or []
            if len(shading_engines) > 1:
                invalid.append(shape)

        return invalid
