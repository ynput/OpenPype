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
                members_list = []
                for member in members:
                    shape = cmds.listRelatives(
                        member, shapes=True, fullPath=True)
                    if not shape:
                        continue
                    members_list = members + shape
                    group_name = "|{}".format(member)
                    if group_name in members_list:
                        members_list.remove(group_name)

                children = get_all_children(members)

                if members_list:
                    children.extend(members_list)
                instance.data["contentMembers"] = children
                self.log.debug("content members: {}".format(children))

            elif objset.endswith("proxy_SET"):
                proxy_members = cmds.ls(members, long=True)
                proxy_list = []
                for proxy in proxy_members:
                    shape = cmds.listRelatives(
                        proxy, shapes=True, fullPath=True)
                    if not shape:
                        continue
                    proxy_list = proxy_members + shape
                    group_name = "|{}".format(proxy)
                    if group_name in proxy_list:
                        proxy_list.remove(group_name)

                set_members = get_all_children(proxy_members)
                if proxy_list:
                    set_members.extend(proxy_list)

                instance.data["proxy"] = set_members
                self.log.debug("proxy members: {}".format(set_members))


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
