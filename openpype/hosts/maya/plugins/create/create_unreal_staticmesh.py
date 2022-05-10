# -*- coding: utf-8 -*-
"""Creator for Unreal Static Meshes."""
from openpype.hosts.maya.api import plugin, lib
from openpype.api import get_project_settings
from openpype.pipeline import legacy_io
from maya import cmds  # noqa


class CreateUnrealStaticMesh(plugin.Creator):
    """Unreal Static Meshes with collisions."""
    name = "staticMeshMain"
    label = "Unreal - Static Mesh"
    family = "staticMesh"
    icon = "cube"
    dynamic_subset_keys = ["asset"]

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(CreateUnrealStaticMesh, self).__init__(*args, **kwargs)
        self._project_settings = get_project_settings(
            legacy_io.Session["AVALON_PROJECT"])

    @classmethod
    def get_dynamic_data(
            cls, variant, task_name, asset_id, project_name, host_name
    ):
        dynamic_data = super(CreateUnrealStaticMesh, cls).get_dynamic_data(
            variant, task_name, asset_id, project_name, host_name
        )
        dynamic_data["asset"] = legacy_io.Session.get("AVALON_ASSET")
        return dynamic_data

    def process(self):
        self.name = "{}_{}".format(self.family, self.name)
        with lib.undo_chunk():
            instance = super(CreateUnrealStaticMesh, self).process()
            content = cmds.sets(instance, query=True)

            # empty set and process its former content
            cmds.sets(content, rm=instance)
            geometry_set = cmds.sets(name="geometry_SET", empty=True)
            collisions_set = cmds.sets(name="collisions_SET", empty=True)

            cmds.sets([geometry_set, collisions_set], forceElement=instance)

            members = cmds.ls(content, long=True) or []
            children = cmds.listRelatives(members, allDescendents=True,
                                          fullPath=True) or []
            children = cmds.ls(children, type="transform")
            for node in children:
                if cmds.listRelatives(node, type="shape"):
                    if [
                        n for n in self.collision_prefixes
                        if node.startswith(n)
                    ]:
                        cmds.sets(node, forceElement=collisions_set)
                    else:
                        cmds.sets(node, forceElement=geometry_set)
