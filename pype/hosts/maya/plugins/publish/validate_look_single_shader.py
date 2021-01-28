from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateSingleShader(pyblish.api.InstancePlugin):
    """Validate all nurbsSurfaces and meshes have exactly one shader assigned.

    This will error if a shape has no shaders or more than one shader.

    """

    order = pype.api.ValidateContentsOrder
    families = ['look']
    hosts = ['maya']
    label = 'Look Single Shader Per Shape'
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    # The default connections to check
    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found shapes which don't have a single shader "
                               "assigned: "
                               "\n{}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):

        # Get all shapes from the instance
        shapes = cmds.ls(instance, type=["nurbsSurface", "mesh"], long=True)

        # Check the number of connected shadingEngines per shape
        no_shaders = []
        more_than_one_shaders = []
        for shape in shapes:
            shading_engines = cmds.listConnections(shape,
                                                   destination=True,
                                                   type="shadingEngine") or []

            # Only interested in unique shading engines.
            shading_engines = list(set(shading_engines))

            if not shading_engines:
                no_shaders.append(shape)
            elif len(shading_engines) > 1:
                more_than_one_shaders.append(shape)

        if no_shaders:
            cls.log.error("No shaders found on: {}".format(no_shaders))
        if more_than_one_shaders:
            cls.log.error("More than one shader found on: "
                          "{}".format(more_than_one_shaders))

        return no_shaders + more_than_one_shaders
