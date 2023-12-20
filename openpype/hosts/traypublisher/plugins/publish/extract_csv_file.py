import os

import pyblish.api

from openpype.pipeline import publish


class ExtractCSVFile(publish.Extractor):
    """
    Extractor export CSV file
    """

    label = "Extract CSV file"
    order = pyblish.api.ExtractorOrder - 0.45
    families = ["editorialcsv"]
    hosts = ["traypublisher"]

    def process(self, instance):

        csv_file_data = instance.data["csvFileData"]

        representation_csv = {
            'name': "csv_data",
            'ext': "csv",
            'files': csv_file_data["filename"],
            "stagingDir": csv_file_data["staging_dir"],
            "stagingDir_persistent": True
        }

        instance.data["representations"].append(representation_csv)

        self.log.info("Added CSV file representation: {}".format(
            representation_csv))
