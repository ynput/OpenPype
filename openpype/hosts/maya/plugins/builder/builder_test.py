from maya import cmds

from openpype.pipeline.action import BuilderAction


class ConnectShape(BuilderAction):
    """Connect Shape within containers.

    Source container will connect to the target containers, by searching for
    matching geometry IDs (cbid).
    Source containers are of family; "animation" and "pointcache".
    The connection with be done with a live world space blendshape.
    """

    label = "Connect Shape"
    icon = "link"
    color = "white"

    def process(self):
        self.log.info("Connect Shape")
        print(cmds.ls())
