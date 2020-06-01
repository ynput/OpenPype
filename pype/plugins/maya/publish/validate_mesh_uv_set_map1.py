from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateMeshUVSetMap1(pyblish.api.InstancePlugin):
    """Validate model's default set exists and is named 'map1'.

    In Maya meshes by default have a uv set named "map1" that cannot be
    deleted. It can be renamed however, introducing some issues with some
    renderers. As such we ensure the first (default) UV set index is named
    "map1".

    """

    order = pype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    optional = True
    label = "Mesh has map1 UV Set"
    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.api.RepairAction]

    @staticmethod
    def get_invalid(instance):

        meshes = cmds.ls(instance, type='mesh', long=True)

        invalid = []
        for mesh in meshes:

            # Get existing mapping of uv sets by index
            indices = cmds.polyUVSet(mesh, query=True, allUVSetsIndices=True)
            maps = cmds.polyUVSet(mesh, query=True, allUVSets=True)
            mapping = dict(zip(indices, maps))

            # Get the uv set at index zero.
            name = mapping[0]
            if name != "map1":
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Meshes found without 'map1' "
                             "UV set: {0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        """Rename uv map at index zero to map1"""

        for mesh in cls.get_invalid(instance):

            # Get existing mapping of uv sets by index
            indices = cmds.polyUVSet(mesh, query=True, allUVSetsIndices=True)
            maps = cmds.polyUVSet(mesh, query=True, allUVSets=True)
            mapping = dict(zip(indices, maps))

            # Ensure there is no uv set named map1 to avoid
            # a clash on renaming the "default uv set" to map1
            existing = set(maps)
            if "map1" in existing:

                # Find a unique name index
                i = 2
                while True:
                    name = "map{0}".format(i)
                    if name not in existing:
                        break
                    i += 1

                cls.log.warning("Renaming clashing uv set name on mesh"
                                " %s to '%s'", mesh, name)

                cmds.polyUVSet(mesh,
                               rename=True,
                               uvSet="map1",
                               newUVSet=name)

            # Rename the initial index to map1
            original = mapping[0]
            cmds.polyUVSet(mesh,
                           rename=True,
                           uvSet=original,
                           newUVSet="map1")
