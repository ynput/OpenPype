from maya import cmds

import pyblish.api


class CollectPointcache(pyblish.api.InstancePlugin):
    """Collect pointcache data for instance."""

    order = pyblish.api.CollectorOrder + 0.4
    families = ["pointcache"]
    label = "Collect Pointcache"
    hosts = ["maya"]

    def process(self, instance):
        if instance.data.get("farm"):
            instance.data["families"].append("publish.farm")

        proxy_set = None
        for node in instance.data["setMembers"]:
            if cmds.nodeType(node) != "objectSet":
                continue
            members = cmds.sets(node, query=True)
            if members is None:
                self.log.warning("Skipped empty objectset: \"%s\" " % node)
                continue
            if node.endswith("proxy_SET"):
                proxy_set = node
                instance.data["proxy"] = []
                instance.data["proxyRoots"] = []
                for member in members:
                    instance.data["proxy"].extend(cmds.ls(member, long=True))
                    instance.data["proxyRoots"].extend(
                        cmds.ls(member, long=True)
                    )
                    instance.data["proxy"].extend(
                        cmds.listRelatives(member, shapes=True, fullPath=True)
                    )
                self.log.debug(
                    "proxy members: {}".format(instance.data["proxy"])
                )

        if proxy_set:
            instance.remove(proxy_set)
            instance.data["setMembers"].remove(proxy_set)
