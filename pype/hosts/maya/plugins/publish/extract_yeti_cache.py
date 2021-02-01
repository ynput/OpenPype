import os
import json

from maya import cmds

import pype.api


class ExtractYetiCache(pype.api.Extractor):
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

        # Yeti related staging dirs
        data_file = os.path.join(dirname, "yeti.fursettings")

        # Collect information for writing cache
        start_frame = instance.data.get("frameStart")
        end_frame = instance.data.get("frameEnd")
        preroll = instance.data.get("preroll")
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
        settings = instance.data.get("fursettings", None)
        if settings is not None:
            with open(data_file, "w") as fp:
                json.dump(settings, fp, ensure_ascii=False)

        # build representations
        if "representations" not in instance.data:
            instance.data["representations"] = []

        self.log.info("cache files: {}".format(cache_files[0]))
        instance.data["representations"].append(
            {
                'name': 'fur',
                'ext': 'fur',
                'files': cache_files[0] if len(cache_files) == 1 else cache_files,
                'stagingDir': dirname,
                'frameStart': int(start_frame),
                'frameEnd': int(end_frame)
            }
        )

        instance.data["representations"].append(
            {
                'name': 'fursettings',
                'ext': 'fursettings',
                'files': os.path.basename(data_file),
                'stagingDir': dirname
            }
        )

        self.log.info("Extracted {} to {}".format(instance, dirname))
