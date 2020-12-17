import os
import json

import pype.api
import pyblish.api

import bpy

class ExtractSetDress(pype.api.Extractor):
    """Extract setdress."""

    label = "Extract SetDress"
    hosts = ["blender"]
    families = ["setdress"]
    optional = True
    order = pyblish.api.ExtractorOrder + 0.1

    def process(self, instance):
        stagingdir = self.staging_dir(instance)

        json_data = []

        for i in instance.context:
            collection = i.data.get('name')
            container = None
            for obj in bpy.data.collections[collection].objects:
                if obj.type == 'ARMATURE':
                    container_name = obj.get('avalon').get('container_name')
                    container = bpy.data.collections[container_name]
            if container:
                json_dict = {}
                json_dict['subset'] = i.data.get('subset')
                json_dict['container'] = container.name
                json_dict['instance_name'] = container.get('avalon').get('instance_name')
                json_data.append(json_dict)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        json_filename = f"{instance.name}.json"
        json_path = os.path.join(stagingdir, json_filename)

        with open(json_path, "w+") as file:
            json.dump(json_data, fp=file, indent=2)

        json_representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(json_representation)

        self.log.info("Extracted instance '{}' to: {}".format(
                      instance.name, json_representation))

