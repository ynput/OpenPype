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
            if objset.endswith("content_SET"):
                members = cmds.ls(members, long=True)
                children = get_all_children(members)
                instance.data["contentMembers"] = children
                # TODO: include another instance.data for content members
                instance.data["contentMembersTransform"] = members
                self.log.debug("content members: {}".format(children))
                self.log.debug(
                    "content members transform : {}".format(members))
            elif objset.endswith("proxy_SET"):
                proxy_members = cmds.ls(members, long=True)
                set_members = get_all_children(proxy_members)
                instance.data["proxy"] = set_members
                instance.data["proxyTransform"] = proxy_members
                # TODO: include another instance.data for proxy
                self.log.debug("proxy members: {}".format(set_members))
                self.log.debug(
                    "proxy members transform: {}".format(proxy_members))

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
