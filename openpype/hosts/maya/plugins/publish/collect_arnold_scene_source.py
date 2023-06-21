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
            if members is None:
                self.log.warning("Skipped empty instance: \"%s\" " % objset)
                continue

            instance.data["contentMembers"] = self.get_ass_data(
                objset, members, "content_SET")
            instance.data["proxy"] = self.get_ass_data(
                objset, members, "proxy_SET")

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

    def get_ass_data(self, objset, members, suffix):
        if objset.endswith(suffix):
            members = cmds.ls(members, long=True)
            if not members:
                return
            children = get_all_children(members)
            members = list(set(members) - set(children))

            return children + members
