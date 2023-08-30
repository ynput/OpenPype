import os
import pyblish.api
from openpype.pipeline import publish


class CollectColorspaceLook(pyblish.api.InstancePlugin,
                            publish.OpenPypePyblishPluginMixin):
    """Collect OCIO colorspace look from LUT file
    """

    label = "Collect Colorspace Look"
    order = pyblish.api.CollectorOrder
    hosts = ["traypublisher"]
    families = ["ociolook"]

    def process(self, instance):
        creator_attrs = instance.data["creator_attributes"]

        lut_repre_name = "LUTfile"
        file_url = creator_attrs["abs_lut_path"]
        file_name = os.path.basename(file_url)
        _, ext = os.path.splitext(file_name)

        # create lut representation data
        lut_repre = {
            "name": lut_repre_name,
            "ext": ext.lstrip("."),
            "files": file_name,
            "stagingDir": os.path.dirname(file_url),
            "tags": []
        }
        instance.data.update({
            "representations": [lut_repre],
            "source": file_url,
            "ocioLookItems": [
                {
                    "name": lut_repre_name,
                    "ext": ext.lstrip("."),
                    "working_colorspace": creator_attrs["working_colorspace"],
                    "input_colorspace": creator_attrs["input_colorspace"],
                    "output_colorspace": creator_attrs["output_colorspace"],
                    "direction": creator_attrs["direction"],
                    "interpolation": creator_attrs["interpolation"]
                }
            ]
        })
