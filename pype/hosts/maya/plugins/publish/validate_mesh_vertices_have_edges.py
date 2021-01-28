import re

from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


def len_flattened(components):
    """Return the length of the list as if it was flattened.

    Maya will return consecutive components as a single entry
    when requesting with `maya.cmds.ls` without the `flatten`
    flag. Though enabling `flatten` on a large list (e.g. millions)
    will result in a slow result. This command will return the amount
    of entries in a non-flattened list by parsing the result with
    regex.

    Args:
        components (list): The non-flattened components.

    Returns:
        int: The amount of entries.

    """
    assert isinstance(components, (list, tuple))
    n = 0

    pattern = re.compile(r"\[(\d+):(\d+)\]")
    for c in components:
        match = pattern.search(c)
        if match:
            start, end = match.groups()
            n += int(end) - int(start) + 1
        else:
            n += 1
    return n


class ValidateMeshVerticesHaveEdges(pyblish.api.InstancePlugin):
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

    order = pype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    category = 'geometry'
    label = 'Mesh Vertices Have Edges'
    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.api.RepairAction]

    @classmethod
    def repair(cls, instance):

        # This fix only works in Maya 2016 EXT2 and newer
        if float(cmds.about(version=True)) <= 2016.0:
            raise RuntimeError("Repair not supported in Maya version below "
                               "2016 EXT 2")

        invalid = cls.get_invalid(instance)
        for node in invalid:
            cmds.polyClean(node, cleanVertices=True)

    @classmethod
    def get_invalid(cls, instance):
        invalid = []

        meshes = cmds.ls(instance, type="mesh", long=True)
        for mesh in meshes:
            num_vertices = cmds.polyEvaluate(mesh, vertex=True)

            # Vertices from all edges
            edges = "%s.e[*]" % mesh
            vertices = cmds.polyListComponentConversion(edges, toVertex=True)
            num_vertices_from_edges = len_flattened(vertices)

            if num_vertices != num_vertices_from_edges:
                invalid.append(mesh)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Meshes found in instance with vertices that "
                               "have no edges: %s" % invalid)
