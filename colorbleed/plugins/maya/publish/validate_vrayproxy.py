import pyblish.api


class ValidateVrayProxy(pyblish.api.InstancePlugin):

    order = pyblish.api.ValidatorOrder
    label = 'VRay Proxy Settings'
    hosts = ['maya']
    families = ['colorbleed.vrayproxy']

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
