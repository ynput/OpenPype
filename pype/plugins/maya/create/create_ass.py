from collections import OrderedDict

import avalon.maya

from maya import cmds


class CreateAss(avalon.maya.Creator):
    """Arnold Archive"""

    name = "ass"
    label = "Ass StandIn"
    family = "ass"
    icon = "cube"
    defaults = ['Main']

    def process(self):
        instance = super(CreateAss, self).process()

        data = OrderedDict(**self.data)

        nodes = list()

        if (self.options or {}).get("useSelection"):
            nodes = cmds.ls(selection=True)

        cmds.sets(nodes, rm=instance)

        assContent = cmds.sets(name="content_SET")
        assProxy = cmds.sets(name="proxy_SET", empty=True)
        cmds.sets([assContent, assProxy], forceElement=instance)

        self.data = data
