# -*- coding: utf-8 -*-
"""Extract Animation as Animaion Library (.anim)."""
import os
import platform

from maya import cmds

import avalon.maya
import openpype.api

from studiolibrarymaya import animitem

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

        name = instance.data["assetEntity"]["name"]
        parents = instance.data["assetEntity"]["data"]["parents"]
        version = "v{}".format(instance.data["version"])
        animlib_path = os.path.join(os.path.join(root_dir, *parents), name, version)

        # Perform extraction
        self.log.info("Performing extraction ...")

        # start studio library export
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
