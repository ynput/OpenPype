import pyblish.api


class CollectFtrackFamilies(pyblish.api.InstancePlugin):
    """Collect family for ftrack publishing
  
    Add ftrack family to those instance that should be published to ftrack

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = 'Add ftrack family'
    families = ["model",
                "setdress",
                "model",
                "animation",
                "look",
                "rig",
                "camera"
                ]
    hosts = ["maya"]

    def process(self, instance):

        # make ftrack publishable
        if instance.data.get('families'):
            instance.data['families'].append('ftrack')
        else:
            instance.data['families'] = ['ftrack']
