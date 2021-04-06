import pyblish.api
import openpype.api


class ValidatOutputNodeExists(pyblish.api.InstancePlugin):
    """Validate if node attribute Create intermediate Directories is turned on

    Rules:
        * The node must have Create intermediate Directories turned on to
        ensure the output file will be created

    """

    order = openpype.api.ValidateContentsOrder
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
        if node.type().name() == "alembic":
            soppath_parm = "sop_path"
        else:
            # Fall back to geometry node
            soppath_parm = "soppath"

        sop_path = node.parm(soppath_parm).eval()
        output_node = hou.node(sop_path)

        if output_node is None:
            cls.log.error("Node at '%s' does not exist" % sop_path)
            result.add(node.path())

        # Added cam as this is a legit output type (cameras can't
        if output_node.type().name() not in ["output", "cam"]:
            cls.log.error("SOP Path does not end path at output node")
            result.add(node.path())

        return result
