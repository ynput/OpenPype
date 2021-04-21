import os
import json
import math

import bpy

from avalon import blender, io
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

        for collection in instance:
            for asset in collection.children:
                collection = bpy.data.collections[asset.name]
                container = bpy.data.collections[asset.name + '_CON']
                metadata = container.get(blender.pipeline.AVALON_PROPERTY)

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
                json_element["asset_name"] = metadata["lib_container"]
                json_element["file_path"] = metadata["libpath"]

                obj = collection.objects[0]

                json_element["transform"] = {
                    "translation": {
                        "x": obj.location.x,
                        "y": obj.location.y,
                        "z": obj.location.z
                    },
                    "rotation": {
                        "x": obj.rotation_euler.x,
                        "y": obj.rotation_euler.y,
                        "z": obj.rotation_euler.z,
                    },
                    "scale": {
                        "x": obj.scale.x,
                        "y": obj.scale.y,
                        "z": obj.scale.z
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
