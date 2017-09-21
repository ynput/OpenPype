from maya import cmds

import pyblish.api


class CollectSetdress(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.499
    label = 'Collect Model Data'
    families = ["colorbleed.setdress"]

    def process(self, instance):
        pass
