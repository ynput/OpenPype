import pyblish.api
import pype.api


class ValidateIntermediateDirectoriesChecked(pyblish.api.InstancePlugin):
    """Validate if node attribute Create intermediate Directories is turned on

    Rules:
        * The node must have Create intermediate Directories turned on to
        ensure the output file will be created

    """

    order = pype.api.ValidateContentsOrder
    families = ["studio.pointcache']
    hosts = ['houdini']
    label = 'Create Intermediate Directories Checked'

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found ROP nodes with Create Intermediate "
                               "Directories turned off")

    @classmethod
    def get_invalid(cls, instance):

        result = []

        for node in instance[:]:
            if node.parm("mkpath").eval() != 1:
                cls.log.error("Invalid settings found on `%s`" % node.path())
                result.append(node.path())

        return result


