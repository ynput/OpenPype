import os
from pprint import pformat
import pyblish.api
from openpype.pipeline import publish
from openpype.pipeline import colorspace


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
        base_name, ext = os.path.splitext(file_name)

        # set output name with base_name which was cleared
        # of all symbols and all parts were capitalized
        output_name = (base_name.replace("_", " ")
                                .replace(".", " ")
                                .replace("-", " ")
                                .title()
                                .replace(" ", ""))

        # get config items
        config_items = instance.data["transientData"]["config_items"]
        config_data = instance.data["transientData"]["config_data"]

        # get colorspace items
        converted_color_data = {}
        for colorspace_key in [
            "working_colorspace",
            "input_colorspace",
            "output_colorspace"
        ]:
            if creator_attrs[colorspace_key]:
                color_data = colorspace.convert_colorspace_enumerator_item(
                    creator_attrs[colorspace_key], config_items)
                converted_color_data[colorspace_key] = color_data
            else:
                converted_color_data[colorspace_key] = None

        # add colorspace to config data
        if converted_color_data["working_colorspace"]:
            config_data["colorspace"] = (
                converted_color_data["working_colorspace"]["name"]
            )

        # create lut representation data
        lut_repre = {
            "name": lut_repre_name,
            "output": output_name,
            "ext": ext.lstrip("."),
            "files": file_name,
            "stagingDir": os.path.dirname(file_url),
            "tags": []
        }
        instance.data.update({
            "representations": [lut_repre],
            "source": file_url,
            "ocioLookWorkingSpace": converted_color_data["working_colorspace"],
            "ocioLookItems": [
                {
                    "name": lut_repre_name,
                    "ext": ext.lstrip("."),
                    "input_colorspace": converted_color_data[
                        "input_colorspace"],
                    "output_colorspace": converted_color_data[
                        "output_colorspace"],
                    "direction": creator_attrs["direction"],
                    "interpolation": creator_attrs["interpolation"],
                    "config_data": config_data
                }
            ],
        })

        self.log.debug(pformat(instance.data))
