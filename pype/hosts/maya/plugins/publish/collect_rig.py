from maya import cmds

import pyblish.api


class CollectRigData(pyblish.api.InstancePlugin):
    """Collect rig data

    Ensures rigs are published to Ftrack.

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = 'Collect Rig Data'
    families = ["rig"]

    def process(self, instance):
        # make ftrack publishable
        if instance.data.get('families'):
            instance.data['families'].append('ftrack')
        else:
            instance.data['families'] = ['ftrack']
