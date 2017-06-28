import os

from maya import cmds

import avalon.maya
import colorbleed.api


class ExtractMayaAscii(colorbleed.api.Extractor):
    """Extract as Maya Ascii"""

    label = "Maya ASCII"
    hosts = ["maya"]
    families = ["colorbleed.rig"]
    optional = True

    def process(self, instance):

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.ma".format(instance.name)
        path = os.path.join(dir_path, filename)

        # Perform extraction
        self.log.info("Performing extraction..")
        with avalon.maya.maintained_selection():
            cmds.select(instance, noExpand=True)
            cmds.file(path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=False,
                      constructionHistory=True)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
