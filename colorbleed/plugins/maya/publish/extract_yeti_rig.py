import os
import json

from maya import cmds
import colorbleed.api


class ExtractYetiProcedural(colorbleed.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Yeti"
    hosts = ["maya"]
    families = ["colorbleed.yetiprocedural"]

    def process(self, instance):
        print instance

        yeti_nodes = cmds.ls(instance, type="pgYetiMaya")
        if not yeti_nodes:
            raise RuntimeError("No pgYetiMaya nodes found in the instance")

        # Define extract output file path
        dirname = self.staging_dir(instance)
        data_file = os.path.join(dirname, "{}.json".format(instance.name))

        start = instance.data.get("startFrame")
        end = instance.data.get("endFrame")
        preroll = instance.data.get("preroll")
        if preroll > 1:
            start -= preroll  # caching supports negative frames

        self.log.info("Writing out cache")
        # Start writing the files
        # <NAME> will be replace by the yeti node name
        filename = "{0}_<NAME>.%04d.fur".format(instance.name)
        path = os.path.join(dirname, filename)
        cache_files = cmds.pgYetiCommand(yeti_nodes,
                                         writeCache=path,
                                         range=(start, end),
                                         sampleTimes="0.0 1.0",
                                         updateViewport=False,
                                         generatePreivew=False)

        self.log.info("Writing metadata file")
        settings = instance.data.get("settings", None)
        if settings is not None:
            with open(data_file, "w") as fp:
                json.dump(settings, fp, ensure_ascii=False)

        # Ensure files can be stored
        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(cache_files)
        instance.data["files"].append(data_file)

        self.log.info("Extracted {} to {}".format(instance, dirname))
