import pyblish.api


class CollectFtrackFamilies(pyblish.api.InstancePlugin):
    """Collect model data

    Ensures always only a single frame is extracted (current frame).

    Note:
        This is a workaround so that the `pype.model` family can use the
        same pointcache extractor implementation as animation and pointcaches.
        This always enforces the "current" frame to be published.

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

    def process(self, instance):

        # make ftrack publishable
        if instance.data.get('families'):
            instance.data['families'].append('ftrack')
        else:
            instance.data['families'] = ['ftrack']
