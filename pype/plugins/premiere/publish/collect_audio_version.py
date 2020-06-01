import pyblish.api


class CollectAudioVersion(pyblish.api.InstancePlugin):
    """


    """

    label = "Collect Audio Version"
    order = pyblish.api.CollectorOrder
    families = ['audio']

    def process(self, instance):
        self.log.info('Audio: {}'.format(instance.data['name']))
        instance.data['version'] = 1
        self.log.info('Audio version to: {}'.format(instance.data['version']))
