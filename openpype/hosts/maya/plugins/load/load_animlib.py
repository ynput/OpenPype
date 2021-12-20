from avalon import api
from maya import cmds
import os


from studiolibrarymaya import animitem

class AnimlibLoader(api.Loader):
    """
    This will run animlib script to create track in scene.

    Supported script types are .py and .mel
    """

    families = ["animlib"]
    representations = ["ma", "mb", "json"]

    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        file_dir = os.path.dirname(self.fname)
        dstObjects = cmds.ls(sl=True, long=True)

        # anim = mutils.Animation.fromPath(file_dir)
        # anim.load(dstObjects)
        animitem.load(file_dir, objects=dstObjects, option="replace all", connect=False, currentTime=False)



        # if file_dir.lower().endswith(".anim"):
        #     else:
        #     self.log.error("Not and animation library file")

        return True
