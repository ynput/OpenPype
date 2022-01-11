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

    def prep_animlib_dir(self, animlib_dir) :
        """rename published files to animlib fixed names

        Args:
            animlib_dir (string): [os path where animlibe files exist]
        """
        animlib_files = [os.path.join(animlib_dir, f)for f in os.listdir(animlib_dir)]
        if (animlib_dir).endswith(".anim") :
            for filepath in animlib_files :
                animlib_name = ("pose" if filepath.endswith(".json") else "animation")
                self.log.info(animlib_name)
                filename = os.path.basename(filepath)
                name = os.path.splitext(filename)[0]

                if name != animlib_name :
                    n_filepath = filepath.replace(filename, filename.replace(name, animlib_name))
                    self.log.info(n_filepath)
                    os.rename(filepath, n_filepath)





    def load(self, context, name, namespace, data):
        file_dir = os.path.dirname(self.fname)
        dstObjects = cmds.ls(sl=True, long=True)

        self.prep_animlib_dir(file_dir)
        self.log.error(file_dir)
        # anim = mutils.Animation.fromPath(file_dir)
        # anim.load(dstObjects)
        # animitem.load(file_dir, objects=dstObjects, option="replace all", connect=False, currentTime=False)



        # if file_dir.lower().endswith(".anim"):
        #     else:
        #     self.log.error("Not and animation library file")

        return True
