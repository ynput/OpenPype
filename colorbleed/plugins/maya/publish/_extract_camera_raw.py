import os

from maya import cmds

import avalon.maya
import colorbleed.api


class ExtractCameraRaw(colorbleed.api.Extractor):
    """Extract as Maya Ascii

    Includes constraints and channels

    """

    label = "Camera Raw (Maya Ascii)"
    hosts = ["maya"]
    families = ["colorbleed.camera"]

    def process(self, instance):

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.raw.ma".format(instance.name)
        path = os.path.join(dir_path, filename)

        # get cameras
        cameras = cmds.ls(instance.data['setMembers'], leaf=True,
                          shapes=True, dag=True, type='camera')

        # Perform extraction
        self.log.info("Performing extraction..")
        with avalon.maya.maintained_selection():
            cmds.select(cameras, noExpand=True)
            cmds.file(path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=False,
                      constructionHistory=False,
                      channels=True,  # allow animation
                      constraints=True,
                      shader=False,
                      expressions=False)

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
