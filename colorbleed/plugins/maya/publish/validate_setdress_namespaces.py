import pyblish.api
import colorbleed.api


class ValidateSetdressNamespaces(pyblish.api.InstancePlugin):
    """Ensure namespaces are not nested"""

    label = "Validate Setdress Namespaces"
    order = pyblish.api.ValidatorOrder
    families = ["colorbleed.setdress"]
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):

        self.log.info("Checking namespace for %s" % instance.name)
        if self.get_invalid(instance):
            raise RuntimeError("Nested namespaces found")

    @classmethod
    def get_invalid(cls, instance):

        from maya import cmds

        invalid = []
        for item in cmds.ls(instance):
            item_parts = item.split("|", 1)[0].rsplit(":")
            if len(item_parts[:-1]) > 1:
                invalid.append(item)

        return invalid
