from maya import cmds

import pyblish.api


class CollectPointcache(pyblish.api.InstancePlugin):
    """Collect pointcache data for instance."""

    order = pyblish.api.CollectorOrder + 0.4
    families = ["pointcache"]
    label = "Collect Pointcache"
    hosts = ["maya"]
    legacy_settings = {
        "write_color_sets": "writeColorSets",
        "write_face_sets": "writeFaceSets",
        "include_user_defined_attributes": "includeUserDefinedAttributes"
    }

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

        # Apply default values not exposed to the user.
        settings = instance.context.data["project_settings"]["maya"]["create"]
        for key, value in settings["CreatePointCache"].items():
            if key.endswith("_editable"):
                continue

            if key in instance.data:
                continue

            if key in self.legacy_settings.keys():
                continue

            self.log.debug(
                "Adding \"{}:{}\" from settings.".format(key, value)
            )
            instance.data[key] = value

        # Backwards compatibility for attributes.
        for key, value in self.legacy_settings.items():
            if key in instance.data:
                self.log.debug(
                    "Using legacy attribute name '{}' since it exists.".format(
                        key
                    )
                )
                instance.data[value] = instance.data.pop(key)

        # Collect user defined attributes.
        if instance.data.get("includeUserDefinedAttributes", False):
            user_defined_attributes = set()
            for node in instance:
                attrs = cmds.listAttr(node, userDefined=True) or list()
                shapes = cmds.listRelatives(node, shapes=True) or list()
                for shape in shapes:
                    attrs.extend(
                        cmds.listAttr(shape, userDefined=True) or list()
                    )

                user_defined_attributes.update(attrs)

            instance.data["userDefinedAttributes"] = list(
                user_defined_attributes
            )
