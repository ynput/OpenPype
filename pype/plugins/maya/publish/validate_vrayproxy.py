import pyblish.api


class ValidateVrayProxy(pyblish.api.InstancePlugin):

    order = pyblish.api.ValidatorOrder
    label = 'VRay Proxy Settings'
    hosts = ['maya']
    families = ['studio.vrayproxy']

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("'%s' has invalid settings for VRay Proxy "
                               "export!" % instance.name)

    @classmethod
    def get_invalid(cls, instance):
        data = instance.data

        if not data["setMembers"]:
            cls.log.error("'%s' is empty! This is a bug" % instance.name)

        if data["animation"]:
            if data["frameEnd"] < data["frameStart"]:
                cls.log.error("End frame is smaller than start frame")
