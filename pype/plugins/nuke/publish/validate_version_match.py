import pyblish.api


class ValidateVersionMatch(pyblish.api.InstancePlugin):
    """Checks if write version matches workfile version"""

    label = "Validate Version Match"
    order = pyblish.api.ValidatorOrder
    hosts = ["nuke"]
    families = ['render.frames']

    def process(self, instance):

        assert instance.data['version'] == instance.context.data['version'], "\
            Version in write doesn't match version of the workfile"
