from maya import cmds

import pyblish.api

from avalon import maya, api
import pype.maya.lib as lib


class CollectMayaRender(pyblish.api.InstancePlugin):
    """Gather all publishable render layers from renderSetup"""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"
    families = ["render"]

    def process(self, instance):
        layers = instance.data['setMembers']
        self.log.debug('layers: {}'.format(layers))

        for layer in layers:
            # test if there are sets (subsets) to attach render to
            sets = cmds.ls(layer, long=True, dag=True, sets=True)
            self.log.debug(sets)
