import os
import json

from maya import cmds

import openpype.api


class ExtractYetiCache(openpype.api.Extractor):
    """Producing Yeti cache files using scene time range.

    This will extract Yeti cache file sequence and fur settings.
    """

    label = "Extract Yeti Cache"
    hosts = ["maya"]
    families = ["yetiRig", "yeticache"]

    def process(self, instance):

        yeti_nodes = cmds.ls(instance, type="pgYetiMaya")
        if not yeti_nodes:
            raise RuntimeError("No pgYetiMaya nodes found in the instance")

        # Define extract output file path
        dirname = self.staging_dir(instance)

        # Collect information for writing cache
        start_frame = instance.data["frameStartHandle"]
        end_frame = instance.data["frameEndHandle"]
        preroll = instance.data["preroll"]
        if preroll > 0:
            start_frame -= preroll

        kwargs = {}
        samples = instance.data.get("samples", 0)
        if samples == 0:
            kwargs.update({"sampleTimes": "0.0 1.0"})
        else:
            kwargs.update({"samples": samples})

        self.log.info(
            "Writing out cache {} - {}".format(start_frame, end_frame))
        # Start writing the files for snap shot
        # <NAME> will be replace by the Yeti node name
        path = os.path.join(dirname, "<NAME>.%04d.fur")
        cmds.pgYetiCommand(yeti_nodes,
                           writeCache=path,
                           range=(start_frame, end_frame),
                           updateViewport=False,
                           generatePreview=False,
                           **kwargs)

        cache_files = [x for x in os.listdir(dirname) if x.endswith(".fur")]

        self.log.info("Writing metadata file")
        settings = instance.data["fursettings"]
        fursettings_path = os.path.join(dirname, "yeti.fursettings")
        with open(fursettings_path, "w") as fp:
            json.dump(settings, fp, ensure_ascii=False)

        # build representations
        if "representations" not in instance.data:
            instance.data["representations"] = []

        self.log.info("cache files: {}".format(cache_files[0]))

        # Workaround: We do not explicitly register these files with the
        # representation solely so that we can write multiple sequences
        # a single Subset without renaming - it's a bit of a hack
        # TODO: Implement better way to manage this sort of integration
        if 'transfers' not in instance.data:
            instance.data['transfers'] = []

        publish_dir = instance.data["publishDir"]
        for cache_filename in cache_files:
            src = os.path.join(dirname, cache_filename)
            dst = os.path.join(publish_dir, os.path.basename(cache_filename))
            instance.data['transfers'].append([src, dst])

        instance.data["representations"].append(
            {
                'name': 'fur',
                'ext': 'fursettings',
                'files': os.path.basename(fursettings_path),
                'stagingDir': dirname
            }
        )

        self.log.info("Extracted {} to {}".format(instance, dirname))
