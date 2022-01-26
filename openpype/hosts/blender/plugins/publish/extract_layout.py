import os
import json

import bpy

from avalon import io
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
import openpype.api


class ExtractLayout(openpype.api.Extractor):
    """Extract a layout."""

    label = "Extract Layout"
    hosts = ["blender"]
    families = ["layout"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        json_data = []

        asset_group = bpy.data.objects[str(instance)]

        for asset in asset_group.children:
            metadata = asset.get(AVALON_PROPERTY)

            parent = metadata["parent"]
            family = metadata["family"]

            self.log.debug("Parent: {}".format(parent))
            blend = io.find_one(
                {
                    "type": "representation",
                    "parent": io.ObjectId(parent),
                    "name": "blend"
                },
                projection={"_id": True})
            blend_id = blend["_id"]

            json_element = {}
            json_element["reference"] = str(blend_id)
            json_element["family"] = family
            json_element["instance_name"] = asset.name
            json_element["asset_name"] = metadata["asset_name"]
            json_element["file_path"] = metadata["libpath"]

            json_element["transform"] = {
                "translation": {
                    "x": asset.location.x,
                    "y": asset.location.y,
                    "z": asset.location.z
                },
                "rotation": {
                    "x": asset.rotation_euler.x,
                    "y": asset.rotation_euler.y,
                    "z": asset.rotation_euler.z,
                },
                "scale": {
                    "x": asset.scale.x,
                    "y": asset.scale.y,
                    "z": asset.scale.z
                }
            }
            json_data.append(json_element)

        json_filename = "{}.json".format(instance.name)
        json_path = os.path.join(stagingdir, json_filename)

        with open(json_path, "w+") as file:
            json.dump(json_data, fp=file, indent=2)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s",
                      instance.name, representation)
