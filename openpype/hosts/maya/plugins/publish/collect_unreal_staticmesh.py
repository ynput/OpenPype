# -*- coding: utf-8 -*-
from maya import cmds  # noqa
import pyblish.api
from avalon.api import Session
from openpype.api import get_project_settings
from pprint import pformat


class CollectUnrealStaticMesh(pyblish.api.InstancePlugin):
    """Collect Unreal Static Mesh."""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Unreal Static Meshes"
    families = ["staticMesh"]

    def process(self, instance):
        project_settings = get_project_settings(Session["AVALON_PROJECT"])
        sm_prefix = (
            project_settings
            ["maya"]
            ["create"]
            ["CreateUnrealStaticMesh"]
            ["static_mesh_prefix"]
        )
        # take the name from instance (without the `staticMesh_` prefix)
        instance.data["staticMeshCombinedName"] = "{}_{}".format(
            sm_prefix,
            instance.data.get("subset")[len(sm_prefix) + 1:])

        self.log.info("joined mesh name: {}".format(
            instance.data.get("staticMeshCombinedName")))

        geometry_set = [i for i in instance if i == "geometry_SET"]
        instance.data["membersToCombine"] = cmds.sets(
            geometry_set, query=True)

        self.log.info("joining meshes: {}".format(
            pformat(instance.data.get("membersToCombine"))))

        collision_set = [i for i in instance if i == "collisions_SET"]
        instance.data["collisionMembers"] = cmds.sets(
            collision_set, query=True)

        self.log.info("collisions: {}".format(
            pformat(instance.data.get("collisionMembers"))))

        # set fbx overrides on instance
        instance.data["smoothingGroups"] = True
        instance.data["smoothMesh"] = True
        instance.data["triangulate"] = True

        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame
