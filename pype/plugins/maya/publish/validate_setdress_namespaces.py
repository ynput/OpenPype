import pyblish.api
import pype.api


class ValidateSetdressNamespaces(pyblish.api.InstancePlugin):
    """Ensure namespaces are not nested

    In the outliner an item in a normal namespace looks as following:
        props_desk_01_:modelDefault

    Any namespace which diverts from that is illegal, example of an illegal
    namespace:
        room_study_01_:props_desk_01_:modelDefault

    """

    label = "Validate Setdress Namespaces"
    order = pyblish.api.ValidatorOrder
    families = ["setdress"]
    actions = [pype.api.SelectInvalidAction]

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
