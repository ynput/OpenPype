from pprint import pformat
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
    """
    label = "Extract Colorspace data"
    order = pyblish.api.ExtractorOrder + 0.49

    allowed_ext = [
        "cin", "dpx", "avi", "dv", "gif", "flv", "mkv", "mov", "mpg", "mpeg",
        "mp4", "m4v", "mxf", "iff", "z", "ifl", "jpeg", "jpg", "jfif", "lut",
        "1dl", "exr", "pic", "png", "ppm", "pnm", "pgm", "pbm", "rla", "rpf",
        "sgi", "rgba", "rgb", "bw", "tga", "tiff", "tif", "img"
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
            if ext.lower() not in self.allowed_ext:
                continue

            # get one filename
            filename = representation["files"]
            if isinstance(filename, list):
                filename = filename.pop()

            # get matching colorspace from rules
            colorspace = get_imagio_colorspace_from_filepath(
                filename, config_path=config_path, file_rules=file_rules
            )

            # infuse data to representation
            if colorspace:
                colorspace_data = {
                    "colorspaceData": {
                        "colorspace": colorspace,
                        "configPath": config_path
                    }
                }
                # look if data key exists
                if not representation.get("data"):
                    representation["data"] = {}

                # update data key
                representation["data"].update(colorspace_data)
                self.log.debug("__ colorspace_data: `{}`".format(
                    pformat(colorspace_data)))

        self.log.info("Config path is : `{}`".format(
            config_path))
