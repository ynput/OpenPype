from avalon import api
from maya import cmds
import os
import tempfile
import shutil

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

    def prep_animlib_dir(self, animlib_dir, animlib_type):
        """rename published files to animlib fixed names

        Args:
            animlib_dir (string): [os path where animlibe files exist]
        """
        # create animlib temp dir
        temp_dir = tempfile.mkdtemp()
        animlib_files = [os.path.join(animlib_dir, f) for f in os.listdir(animlib_dir)]
        for filepath in animlib_files:
            animlib_name = "pose" if filepath.endswith(".json") else "animation"
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)
            temp_filepath = os.path.join(temp_dir, animlib_name + ext)
            shutil.copy2(filepath, temp_filepath)
        return temp_dir

    def load(self, context, name, namespace, data):
        file_dir = os.path.dirname(self.fname)
        dstObjects = cmds.ls(sl=True, long=True)

        # animlib_type = data["animlib_type"]
        animlib_type = ".anim"  # for example

        temp_dir = self.prep_animlib_dir(file_dir, animlib_type)
        self.log.error(temp_dir)
        # anim = mutils.Animation.fromPath(file_dir)
        # anim.load(dstObjects)
        animitem.load(
            temp_dir,
            objects=dstObjects,
            option="replace all",
            connect=False,
            currentTime=False,
        )

        # Cleanup the temp directory
        shutil.rmtree(temp_dir)

        return True
