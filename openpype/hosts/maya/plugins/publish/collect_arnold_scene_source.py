from maya import cmds

import pyblish.api
from openpype.hosts.maya.api.lib import get_all_children


class CollectArnoldSceneSource(pyblish.api.InstancePlugin):
    """Collect Arnold Scene Source data."""

    # Offset to be after renderable camera collection.
    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Arnold Scene Source"
    families = ["ass"]

    def process(self, instance):
        objsets = instance.data["setMembers"]

        for objset in objsets:
            objset = str(objset)
            members = cmds.sets(objset, query=True)
            members = cmds.ls(members, long=True)
            if members is None:
                self.log.warning("Skipped empty instance: \"%s\" " % objset)
                continue
            if objset.endswith("content_SET"):
                children = get_all_children(members)
                instance.data["contentMembers"] = children + members
                self.log.debug(
                    "content members: {}".format(
                        instance.data["contentMembers"]
                    )
                )
            elif objset.endswith("proxy_SET"):
                children = get_all_children(cmds.ls(members, long=True))
                instance.data["proxy"] = children + members
                self.log.debug(
                    "proxy members: {}".format(instance.data["proxy"])
                )

        # Use camera in object set if present else default to render globals
        # camera.
        cameras = cmds.ls(type="camera", long=True)
        renderable = [c for c in cameras if cmds.getAttr("%s.renderable" % c)]
        if renderable:
            camera = renderable[0]
            for node in instance.data["contentMembers"]:
                camera_shapes = cmds.listRelatives(
                    node, shapes=True, type="camera"
                )
                if camera_shapes:
                    camera = node
            instance.data["camera"] = camera
        else:
            self.log.debug("No renderable cameras found.")

        self.log.debug("data: {}".format(instance.data))
