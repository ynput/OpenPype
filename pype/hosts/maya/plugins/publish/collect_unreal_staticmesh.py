# -*- coding: utf-8 -*-
from maya import cmds
import pyblish.api


class CollectUnrealStaticMesh(pyblish.api.InstancePlugin):
    """Collect unreal static mesh

    Ensures always only a single frame is extracted (current frame). This
    also sets correct FBX options for later extraction.

    Note:
        This is a workaround so that the `pype.model` family can use the
        same pointcache extractor implementation as animation and pointcaches.
        This always enforces the "current" frame to be published.

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Model Data"
    families = ["unrealStaticMesh"]

    def process(self, instance):
        # add fbx family to trigger fbx extractor
        instance.data["families"].append("fbx")
        # set fbx overrides on instance
        instance.data["smoothingGroups"] = True
        instance.data["smoothMesh"] = True
        instance.data["triangulate"] = True

        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame
