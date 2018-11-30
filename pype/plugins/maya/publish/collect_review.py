from maya import cmds

import pyblish.api

class CollectReviewData(pyblish.api.InstancePlugin):
    """Collect Review data

    """

    order = pyblish.api.CollectorOrder + 0.499
    label = 'Collect Review Data'
    families = ["review"]

    def process(self, instance):

        # make ftrack publishable
        instance.data["families"] = ['ftrack']
