from collections import OrderedDict

import avalon.maya
from pype.hosts.maya import lib

from maya import cmds


class CreateAss(avalon.maya.Creator):
    """Arnold Archive"""

    name = "ass"
    label = "Ass StandIn"
    family = "ass"
    icon = "cube"
    defaults = ['Main']

    def __init__(self, *args, **kwargs):
        super(CreateAss, self).__init__(*args, **kwargs)

        # Add animation data
        self.data.update(lib.collect_animation_data())

        # Vertex colors with the geometry
        self.data["exportSequence"] = False

    def process(self):
        instance = super(CreateAss, self).process()

        # data = OrderedDict(**self.data)



        nodes = list()

        if (self.options or {}).get("useSelection"):
            nodes = cmds.ls(selection=True)

        cmds.sets(nodes, rm=instance)

        assContent = cmds.sets(name="content_SET")
        assProxy = cmds.sets(name="proxy_SET", empty=True)
        cmds.sets([assContent, assProxy], forceElement=instance)

        # self.log.info(data)
        #
        # self.data = data
