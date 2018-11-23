import pyblish.api


class CollectFtrackInstance(pyblish.api.InstancePlugin):
    """Collect ftrack component data

    Add empty ftrack components to instance.


    """

    order = pyblish.api.CollectorOrder + 0.4
    label = 'Collect Ftrack Components'

    def process(self, instance):
        components = {}
        instance.data['ftrackComponents'] = components
