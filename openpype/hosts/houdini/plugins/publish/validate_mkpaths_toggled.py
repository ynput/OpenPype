import pyblish.api
from openpype.pipeline.publish import ValidateContentsOrder


class ValidateIntermediateDirectoriesChecked(pyblish.api.InstancePlugin):
    """Validate Create Intermediate Directories is enabled on ROP node."""

    order = ValidateContentsOrder
    families = ["pointcache", "camera", "vdbcache"]
    hosts = ["houdini"]
    label = "Create Intermediate Directories Checked"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Found ROP node with Create Intermediate "
                "Directories turned off: %s" % invalid
            )

    @classmethod
    def get_invalid(cls, instance):

        result = []

        for node in instance[:]:
            if node.parm("mkpath").eval() != 1:
                cls.log.error("Invalid settings found on `%s`" % node.path())
                result.append(node.path())

        return result
