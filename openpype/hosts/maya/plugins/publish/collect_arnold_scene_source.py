from maya import cmds

import pyblish.api
from openpype.hosts.maya.api.lib import get_all_children


class CollectArnoldSceneSource(pyblish.api.InstancePlugin):
    """Collect Arnold Scene Source data."""

    # Offset to be after renderable camera collection.
    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Arnold Scene Source"
    families = ["ass", "assProxy"]

    def process(self, instance):
        instance.data["members"] = []
        for set_member in instance.data["setMembers"]:
            if cmds.nodeType(set_member) != "objectSet":
                instance.data["members"].extend(self.get_hierarchy(set_member))
                continue

            members = cmds.sets(set_member, query=True)
            members = cmds.ls(members, long=True)
            if members is None:
                self.log.warning(
                    "Skipped empty instance: \"%s\" " % set_member
                )
                continue
            if set_member.endswith("proxy_SET"):
                instance.data["proxy"] = self.get_hierarchy(members)

        # Use camera in object set if present else default to render globals
        # camera.
        cameras = cmds.ls(type="camera", long=True)
        renderable = [c for c in cameras if cmds.getAttr("%s.renderable" % c)]
        if renderable:
            camera = renderable[0]
            for node in instance.data["members"]:
                camera_shapes = cmds.listRelatives(
                    node, shapes=True, type="camera"
                )
                if camera_shapes:
                    camera = node
            instance.data["camera"] = camera
        else:
            self.log.debug("No renderable cameras found.")

        self.log.debug("data: {}".format(instance.data))

    def get_hierarchy(self, nodes):
        """Return nodes with all their children"""
        nodes = cmds.ls(nodes, long=True)
        if not nodes:
            return []
        children = get_all_children(nodes)
        # Make sure nodes merged with children only
        # contains unique entries
        return list(set(nodes + children))
