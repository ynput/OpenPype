# -*- coding: utf-8 -*-
from maya import cmds  # noqa
import pyblish.api
from pprint import pformat


class CollectUnrealStaticMesh(pyblish.api.InstancePlugin):
    """Collect Unreal Static Mesh."""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Unreal Static Meshes"
    families = ["staticMesh"]

    def process(self, instance):
        geometry_set = [i for i in instance if i == "geometry_SET"]
        instance.data["geometryMembers"] = cmds.sets(
            geometry_set, query=True)

        self.log.info("geometry: {}".format(
            pformat(instance.data.get("geometryMembers"))))

        collision_set = [i for i in instance if i == "collisions_SET"]
        instance.data["collisionMembers"] = cmds.sets(
            collision_set, query=True)

        self.log.info("collisions: {}".format(
            pformat(instance.data.get("collisionMembers"))))

        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame
