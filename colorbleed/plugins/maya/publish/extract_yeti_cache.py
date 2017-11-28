import os
import json

from maya import cmds

import colorbleed.api
# from cb.utils.maya import context


class ExtractYetiCache(colorbleed.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Yeti Cache"
    hosts = ["maya"]
    families = ["colorbleed.yetiRig", "colorbleed.yeticache"]

    def process(self, instance):

        yeti_nodes = cmds.ls(instance, type="pgYetiMaya")
        if not yeti_nodes:
            raise RuntimeError("No pgYetiMaya nodes found in the instance")

        # Define extract output file path
        dirname = self.staging_dir(instance)

        # Yeti related staging dirs
        data_file = os.path.join(dirname, "yeti_settings.json")

        # Collect information for writing cache
        start_frame = instance.data.get("startFrame")
        end_frame = instance.data.get("endFrame")
        preroll = instance.data.get("preroll")
        if preroll > 0:
            start_frame -= preroll

        self.log.info("Writing out cache")
        # Start writing the files for snap shot
        # <NAME> will be replace by the Yeti node name
        path = os.path.join(dirname, "cache_<NAME>.0001.fur")
        cmds.pgYetiCommand(yeti_nodes,
                           writeCache=path,
                           range=(start_frame, end_frame),
                           sampleTimes="0.0 1.0",
                           updateViewport=False,
                           generatePreview=False)

        cache_files = [x for x in os.listdir(dirname) if x.endswith(".fur")]

        self.log.info("Writing metadata file")
        settings = instance.data.get("settings", None)
        if settings is not None:
            with open(data_file, "w") as fp:
                json.dump(settings, fp, ensure_ascii=False)

        # Ensure files can be stored
        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].extend([cache_files,
                                       "yeti_settings.json"])

        self.log.info("Extracted {} to {}".format(instance, dirname))

        cmds.select(clear=True)
