from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import ValidateMeshOrder
from openpype.hosts.maya.api.lib import len_flattened


class ValidateMeshHasUVs(pyblish.api.InstancePlugin):
    """Validate the current mesh has UVs.

    It validates whether the current UV set has non-zero UVs and
    at least more than the vertex count. It's not really bulletproof,
    but a simple quick validation to check if there are likely
    UVs for every face.
    """

    order = ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    label = 'Mesh Has UVs'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = True

    @classmethod
    def get_invalid(cls, instance):
        invalid = []

        for node in cmds.ls(instance, type='mesh'):
            num_vertices = cmds.polyEvaluate(node, vertex=True)

            if num_vertices == 0:
                cls.log.warning(
                    "Skipping \"{}\", cause it does not have any "
                    "vertices.".format(node)
                )
                continue

            uv = cmds.polyEvaluate(node, uv=True)

            if uv == 0:
                invalid.append(node)
                continue

            vertex = cmds.polyEvaluate(node, vertex=True)
            if uv < vertex:
                # Workaround:
                # Maya can have instanced UVs in a single mesh, for example
                # imported from an Alembic. With instanced UVs the UV count
                # from `maya.cmds.polyEvaluate(uv=True)` will only result in
                # the unique UV count instead of for all vertices.
                #
                # Note: Maya can save instanced UVs to `mayaAscii` but cannot
                #       load this as instanced. So saving, opening and saving
                #       again will lose this information.
                map_attr = "{}.map[*]".format(node)
                uv_to_vertex = cmds.polyListComponentConversion(map_attr,
                                                                toVertex=True)
                uv_vertex_count = len_flattened(uv_to_vertex)
                if uv_vertex_count < vertex:
                    invalid.append(node)
                else:
                    cls.log.warning("Node has instanced UV points: "
                                    "{0}".format(node))

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Meshes found in instance without "
                               "valid UVs: {0}".format(invalid))
