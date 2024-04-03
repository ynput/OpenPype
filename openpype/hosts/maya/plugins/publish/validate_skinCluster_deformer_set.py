from maya import cmds

import pyblish.api

import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    OptionalPyblishPluginMixin
)


class ValidateSkinclusterDeformerSet(pyblish.api.InstancePlugin,
                                     OptionalPyblishPluginMixin):
    """Validate skinClusters on meshes have valid member relationships.

    In rare cases it can happen that a mesh has a skinCluster in its history
    but it is *not* included in the deformer relationship history. If this is
    the case then FBX will not export the skinning.

    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ['fbx']
    label = "Skincluster Deformer Relationships"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = False

    def process(self, instance):
        """Process all the transform nodes in the instance"""
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Invalid skinCluster relationships "
                             "found on meshes: {0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):

        meshes = cmds.ls(instance, type="mesh", noIntermediate=True, long=True)
        invalid = list()

        for mesh in meshes:
            history = cmds.listHistory(mesh) or []
            skins = cmds.ls(history, type="skinCluster")

            # Ensure at most one skinCluster
            assert len(skins) <= 1, "Cannot have more than one skinCluster"

            if skins:
                skin = skins[0]

                # Ensure the mesh is also in the skinCluster set
                # otherwise the skin will not be exported correctly
                # by the FBX Exporter.
                deformer_sets = cmds.listSets(object=mesh, type=2)
                for deformer_set in deformer_sets:
                    used_by = cmds.listConnections(deformer_set + ".usedBy",
                                                   source=True,
                                                   destination=False)

                    # Ignore those that don't seem to have a usedBy connection
                    if not used_by:
                        continue

                    # We have a matching deformer set relationship
                    if skin in set(used_by):
                        break

                else:
                    invalid.append(mesh)
                    cls.log.warning(
                        "Mesh has skinCluster in history but is not included "
                        "in its deformer relationship set: "
                        "{0} (skinCluster: {1})".format(mesh, skin)
                    )

        return invalid
