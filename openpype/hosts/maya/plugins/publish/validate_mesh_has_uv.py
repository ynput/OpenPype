import pyblish.api
from maya import cmds

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api.lib import len_flattened
from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateMeshOrder,
)


class ValidateMeshHasUVs(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
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
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:

            names = "<br>".join(
                " - {}".format(node) for node in invalid
            )

            raise PublishValidationError(
                title="Mesh has missing UVs",
                message="Model meshes are required to have UVs.<br><br>"
                        "Meshes detected with invalid or missing UVs:<br>"
                        "{0}".format(names)
            )
