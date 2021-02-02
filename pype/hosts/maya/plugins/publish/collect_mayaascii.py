from maya import cmds

import pyblish.api


class CollectMayaAscii(pyblish.api.InstancePlugin):
    """Collect May Ascii Data

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = 'Collect Model Data'
    families = ["mayaAscii"]

    def process(self, instance):
        # Extract only current frame (override)
        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame

        # make ftrack publishable
        if instance.data.get('families'):
            instance.data['families'].append('ftrack')
        else:
            instance.data['families'] = ['ftrack']
