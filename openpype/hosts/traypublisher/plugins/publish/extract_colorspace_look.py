import os
import json
import pyblish.api
from openpype.pipeline import publish


class ExtractColorspaceLook(publish.Extractor,
                            publish.OpenPypePyblishPluginMixin):
    """Extract OCIO colorspace look from LUT file
    """

    label = "Extract Colorspace Look"
    order = pyblish.api.ExtractorOrder
    hosts = ["traypublisher"]
    families = ["ociolook"]

    def process(self, instance):
        ociolook_items = instance.data["ocioLookItems"]
        ociolook_working_color = instance.data["ocioLookWorkingSpace"]
        staging_dir = self.staging_dir(instance)

        # create ociolook file attributes
        ociolook_file_name = "ocioLookFile.json"
        ociolook_file_content = {
            "version": 1,
            "data": {
                "ocioLookItems": ociolook_items,
                "ocioLookWorkingSpace": ociolook_working_color
            }
        }

        # write ociolook content into json file saved in staging dir
        file_url = os.path.join(staging_dir, ociolook_file_name)
        with open(file_url, "w") as f_:
            json.dump(ociolook_file_content, f_, indent=4)

        # create lut representation data
        ociolook_repre = {
            "name": "ocioLookFile",
            "ext": "json",
            "files": ociolook_file_name,
            "stagingDir": staging_dir,
            "tags": []
        }
        instance.data["representations"].append(ociolook_repre)
