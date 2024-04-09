import pyblish.api
from maya import cmds

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api.lib import len_flattened
from openpype.pipeline.publish import (
    PublishValidationError,
    RepairAction,
    ValidateMeshOrder,
    OptionalPyblishPluginMixin
)


class ValidateMeshVerticesHaveEdges(pyblish.api.InstancePlugin,
                                    OptionalPyblishPluginMixin):
    """Validate meshes have only vertices that are connected to edges.

    Maya can have invalid geometry with vertices that have no edges or
    faces connected to them.

    In Maya 2016 EXT 2 and later there's a command to fix this:
        `maya.cmds.polyClean(mesh, cleanVertices=True)`

    In older versions of Maya it works to select the invalid vertices
    and merge the components.

    To find these invalid vertices select all vertices of the mesh
    that are visible in the viewport (drag to select), afterwards
    invert your selection (Ctrl + Shift + I). The remaining selection
    contains the invalid vertices.

    """

    order = ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    label = 'Mesh Vertices Have Edges'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               RepairAction]
    optional = True

    @classmethod
    def repair(cls, instance):

        # This fix only works in Maya 2016 EXT2 and newer
        if float(cmds.about(version=True)) <= 2016.0:
            raise PublishValidationError(
                ("Repair not supported in Maya version below "
                 "2016 EXT 2"))

        invalid = cls.get_invalid(instance)
        for node in invalid:
            cmds.polyClean(node, cleanVertices=True)

    @classmethod
    def get_invalid(cls, instance):
        invalid = []

        meshes = cmds.ls(instance, type="mesh", long=True)
        for mesh in meshes:
            num_vertices = cmds.polyEvaluate(mesh, vertex=True)

            if num_vertices == 0:
                cls.log.warning(
                    "Skipping \"{}\", cause it does not have any "
                    "vertices.".format(mesh)
                )
                continue

            # Vertices from all edges
            edges = "%s.e[*]" % mesh
            vertices = cmds.polyListComponentConversion(edges, toVertex=True)
            num_vertices_from_edges = len_flattened(vertices)

            if num_vertices != num_vertices_from_edges:
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                ("Meshes found in instance with vertices that "
                 "have no edges: {}").format(invalid))
