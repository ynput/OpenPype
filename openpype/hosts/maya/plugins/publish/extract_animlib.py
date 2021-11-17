# -*- coding: utf-8 -*-
"""Extract animlib as Maya Scene."""
import os

from maya import cmds

import avalon.maya
import openpype.api


class ExtractAnimLib(openpype.api.Extractor):
    """Extract animlib as Maya Scene."""

    label = "Extract AnimLib"
    hosts = ["maya"]
    families = ["animation"]
    scene_type = "anim"

    def process(self, instance):
        """Plugin entry point."""

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(dir_path, filename)

        # Perform extraction
        self.log.info("Performing extraction ...")
        with avalon.maya.maintained_selection():
            cmds.select(instance, noExpand=True)
            # start studio library export

            # cmds.file(path,
            #           force=True,
            #           typ="mayaAscii" if self.scene_type == "ma" else "mayaBinary",  # noqa: E501
            #           exportSelected=True,
            #           preserveReferences=False,
            #           channels=True,
            #           constraints=True,
            #           expressions=True,
            #           constructionHistory=True)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': filename,
            "stagingDir": dir_path
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
