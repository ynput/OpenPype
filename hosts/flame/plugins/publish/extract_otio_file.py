import os
import pyblish.api
import openpype.api
import opentimelineio as otio


class ExtractOTIOFile(openpype.api.Extractor):
    """
    Extractor export OTIO file
    """

    label = "Extract OTIO file"
    order = pyblish.api.ExtractorOrder - 0.45
    families = ["workfile"]
    hosts = ["flame"]

    def process(self, instance):
        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        name = instance.data["name"]
        staging_dir = self.staging_dir(instance)

        otio_timeline = instance.context.data["otioTimeline"]
        # create otio timeline representation
        otio_file_name = name + ".otio"
        otio_file_path = os.path.join(staging_dir, otio_file_name)

        # export otio file to temp dir
        otio.adapters.write_to_file(otio_timeline, otio_file_path)

        representation_otio = {
            'name': "otio",
            'ext': "otio",
            'files': otio_file_name,
            "stagingDir": staging_dir,
        }

        instance.data["representations"].append(representation_otio)

        self.log.info("Added OTIO file representation: {}".format(
            representation_otio))
