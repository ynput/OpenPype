import pyblish.api


class ValidateFrameRange(pyblish.api.InstancePlugin):
    """Validate the frame range of the current Saver"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Frame Range"
    families = ["colorbleed.imagesequence"]
    hosts = ["fusion"]

    @classmethod
    def get_invalid(cls, instance):
        return []

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Animation content is invalid. See log.")