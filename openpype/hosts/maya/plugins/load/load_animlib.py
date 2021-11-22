from avalon import api
from maya import cmds
import os

import os
import sys

if not os.path.exists(r'/Users/karimbehiry/Documents/git/studiolibrary-2.9.6.b3/src'):
    raise IOError(r'The source path "/Users/karimbehiry/Documents/git/studiolibrary-2.9.6.b3/src" does not exist!')

if r'/Users/karimbehiry/Documents/git/studiolibrary-2.9.6.b3/src' not in sys.path:
    sys.path.insert(0, r'/Users/karimbehiry/Documents/git/studiolibrary-2.9.6.b3/src')

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
