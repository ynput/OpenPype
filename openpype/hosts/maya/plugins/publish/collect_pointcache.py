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
        for node in cmds.ls(instance.data["setMembers"],
                            exactType="objectSet"):
            # Find proxy_SET objectSet in the instance for proxy meshes
            if node.endswith("proxy_SET"):
                members = cmds.sets(node, query=True)
                if members is None:
                    self.log.debug("Skipped empty proxy_SET: \"%s\" " % node)
                    continue
                self.log.debug("Found proxy set: {}".format(node))

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
                    "Found proxy members: {}".format(instance.data["proxy"])
                )
                break

        if proxy_set:
            instance.remove(proxy_set)
            instance.data["setMembers"].remove(proxy_set)

        # Collect user defined attributes.
        if not instance.data.get("includeUserDefinedAttributes", False):
            return

        user_defined_attributes = set()
        for node in instance:
            attrs = cmds.listAttr(node, userDefined=True) or list()
            shapes = cmds.listRelatives(node, shapes=True) or list()
            for shape in shapes:
                attrs.extend(cmds.listAttr(shape, userDefined=True) or list())

            user_defined_attributes.update(attrs)

        instance.data["userDefinedAttributes"] = list(user_defined_attributes)
