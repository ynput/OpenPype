import pyblish.api
import colorbleed.api


class ValidatOutputNodeExists(pyblish.api.InstancePlugin):
    """Validate if node attribute Create intermediate Directories is turned on

    Rules:
        * The node must have Create intermediate Directories turned on to
        ensure the output file will be created

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ["*"]
    hosts = ['houdini']
    label = "Output Node Exists"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Could not find output node(s)!")

    @classmethod
    def get_invalid(cls, instance):

        import hou

        result = set()

        node = instance[0]
        sop_path = node.parm("sop_path").eval()
        if not sop_path.endswith("OUT"):
            cls.log.error("SOP Path does not end path at output node")
            result.add(node.path())

        if hou.node(sop_path) is None:
            cls.log.error("Node at '%s' does not exist" % sop_path)
            result.add(node.path())

        return result
