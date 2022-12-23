import os
import pyblish.api
from openpype.pipeline import publish
from openpype.pipeline import (
    get_imagio_colorspace_from_filepath
)

class ExtractColorspaceData(publish.Extractor):
    """ Inject Colorspace data to available representations.

    Input data:
    - context.data[colorspace_config_path]:
        for resolving project and host related config.ocio
    - context.data[colorspace_file_rules]:
        for resolving matched file rule from representation file name
        and adding it to representation

    Output data:
        representation[data] = {
            "colorspaceData": {
                "colorspace": "linear",
                "configPath": "/path/to/config.ocio"
            }
        }

    TODO:
        - rootify config path so it can be single path for usecases
          where windows submit to farm and farm on linux do
          oiio conversions.
        - where to put the data so they are integrated to db representation
    """
    label = "Extract Colorspace data"
    order = pyblish.api.ExtractorOrder + 0.49

    allowed_ext = [
        "mov", "exr", "dpx", "mp4", "jpg", "jpeg", "tiff", "tif"
    ]
    def process(self, instance):
        representations = instance.data.get("representations")
        if not representations:
            self.log.info("No representations at instance : `{}`".format(
                instance))
            return

        # get colorspace settings
        ctx = instance.context
        config_path = ctx.data["colorspace_config_path"]
        file_rules = ctx.data["colorspace_file_rules"]

        # loop representations
        for representation in representations:
            # check extension
            ext = representation["ext"]
            if ext not in self.allowed_ext:
                continue

            # get one filename
            filename = representation["files"]
            if isinstance(filename, list):
                filename = filename.pop()

            colorspace = get_imagio_colorspace_from_filepath(
                filename, config_path=config_path, file_rules=file_rules
            )

            if colorspace:
                representation["data"] = {
                    "colorspaceData": {
                        "colorspace": colorspace,
                        "configPath": config_path
                    }
                }
        self.log.info("Config path is : `{}`".format(
            config_path))
