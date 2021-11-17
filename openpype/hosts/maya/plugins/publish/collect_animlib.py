from maya import cmds

import pyblish.api


class CollectAnimLibData(pyblish.api.InstancePlugin):
    """Collect animlib data

    Ensures animlibs are published.

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = 'Collect AnimLib Data'
    families = ["animlib"]

    def process(self, instance):
        # make ftrack publishable
        if instance.data.get('families'):
            instance.data['families'].append('ftrack')
        else:
            instance.data['families'] = ['ftrack']
