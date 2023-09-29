import os

from maya import cmds

from openpype.pipeline import publish


class ExtractYetiCache(publish.Extractor):
    """Producing Yeti cache files using scene time range.

    This will extract Yeti cache file sequence and fur settings.
    """

    label = "Extract Yeti Cache"
    hosts = ["maya"]
    families = ["yeticacheUE"]

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

        self.log.debug(f"Writing out cache {start_frame} - {end_frame}")
        filename = f"{instance.name}.abc"
        path = os.path.join(dirname, filename)
        cmds.pgYetiCommand(yeti_nodes,
                           writeAlembic=path,
                           range=(start_frame, end_frame),
                           asUnrealAbc=True,
                           **kwargs)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': filename,
            'stagingDir': dirname
        }
        instance.data["representations"].append(representation)

        self.log.debug(f"Extracted {instance} to {dirname}")
