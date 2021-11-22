# -*- coding: utf-8 -*-
"""Extract Animation as Animaion Library (.anim)."""
import os
import platform

from maya import cmds

import avalon.maya
import openpype.api


import os
import sys

if not os.path.exists(r'/Users/karimbehiry/Documents/git/studiolibrary-2.9.6.b3/src'):
    raise IOError(r'The source path "/Users/karimbehiry/Documents/git/studiolibrary-2.9.6.b3/src" does not exist!')

if r'/Users/karimbehiry/Documents/git/studiolibrary-2.9.6.b3/src' not in sys.path:
    sys.path.insert(0, r'/Users/karimbehiry/Documents/git/studiolibrary-2.9.6.b3/src')

from studiolibrarymaya import animitem
# import mutils
# import mutils.gui

class ExtractAnimLib(openpype.api.Extractor):
    """Extract Animation as Animaion Library (.anim)."""

    label = "Extract AnimLib"
    hosts = ["maya"]
    families = ["animlib"]
    scene_type = "anim"

    def process(self, instance):
        """Plugin entry point."""

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(dir_path, filename)

        current_platform = platform.system().lower()
        root_dir = instance.context.data["project_settings"]["maya"]["create"]["CreateAnimlib"]["exportdir"][current_platform]
        animlib_path = os.path.join(root_dir, filename)

        # Perform extraction
        self.log.info("Performing extraction ...")
        # with avalon.maya.maintained_selection():
        # cmds.select(instance, noExpand=True)
        # start studio library export

        # path = "/AnimLibrary/Characters/Malcolm/malcolm.anim"
        objects = instance.data["setMembers"]
        startFrame= instance.data["frameStart"] # get start keyframe instead of playback range
        endFrame= instance.data["frameEnd"]

        # Saving an animlib item to Root
        animitem.save(animlib_path,
                        objects=objects,
                        startFrame=startFrame,
                        endFrame=endFrame,
                        fileType="mayaAscii",
                        # bakeConnected=False
                        )
        self.log.info("Extracted instance '%s' to: %s" % (instance.name, animlib_path))

        # Saving an animlib item
        animitem.save(path,
                        objects=objects,
                        startFrame=startFrame,
                        endFrame=endFrame,
                        fileType="mayaAscii",
                        # bakeConnected=False
                        )

        animlib_ma_files = [x for x in os.listdir(path) if x.endswith(".ma")]
        animlib_json_files = [x for x in os.listdir(path) if x.endswith(".json")]

        # build representations
        if "representations" not in instance.data:
            instance.data["representations"] = []

        instance.data["representations"].append(
            {
                'name': "ma",
                'ext': "ma",
                'files': animlib_ma_files[0],
                "stagingDir": path
            }
        )

        instance.data["representations"].append(
            {
                'name': "json",
                'ext': "json",
                'files': animlib_json_files[0],
                "stagingDir": path
            }
        )

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
