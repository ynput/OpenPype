import avalon.maya
from maya import cmds


class CreateRig(avalon.maya.Creator):
    """Skeleton and controls for manipulation of the geometry"""

    name = "rigDefault"
    label = "Rig"
    family = "colorbleed.rig"

    def process(self):
        instance = super(CreateRig, self).process()

        controls = cmds.sets(name="controls_SET", empty=True)
        pointcache = cmds.sets(name="pointcache_SET", empty=True)
        cmds.sets([controls, pointcache], forceElement=instance)
