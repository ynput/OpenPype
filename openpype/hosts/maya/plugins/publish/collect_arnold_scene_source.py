from maya import cmds

import pyblish.api


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
            if members is None:
                self.log.warning("Skipped empty instance: \"%s\" " % objset)
                continue
            if objset.endswith("content_SET"):
                instance.data["setMembers"] = cmds.ls(members, long=True)
                self.log.debug("content members: {}".format(members))
            elif objset.endswith("proxy_SET"):
                instance.data["proxy"] = cmds.ls(members, long=True)
                self.log.debug("proxy members: {}".format(members))

        # Use camera in object set if present else default to render globals
        # camera.
        cameras = cmds.ls(type="camera", long=True)
        renderable = [c for c in cameras if cmds.getAttr("%s.renderable" % c)]
        camera = renderable[0]
        for node in instance.data["setMembers"]:
            camera_shapes = cmds.listRelatives(
                node, shapes=True, type="camera"
            )
            if camera_shapes:
                camera = node
        instance.data["camera"] = camera

        self.log.debug("data: {}".format(instance.data))
