import json
import os

import unreal

import openpype.api
from avalon import io


class ExtractLook(openpype.api.Extractor):
    """Extract look."""

    label = "Extract Look"
    hosts = ["unreal"]
    families = ["look"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        resources_dir = instance.data["resourcesDir"]

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        transfers = []

        json_data = []

        for member in instance:
            asset = ar.get_asset_by_object_path(member)
            object = asset.get_asset()

            name = asset.get_editor_property('asset_name')

            fbx_filename = f"{instance.name}_{name}.fbx"

            fbx_exporter = unreal.StaticMeshExporterFBX()
            fbx_exporter.set_editor_property('text', False)

            options = unreal.FbxExportOption()
            options.set_editor_property('ascii', False)
            options.set_editor_property('collision', False)

            task = unreal.AssetExportTask()
            task.set_editor_property('exporter', fbx_exporter)
            task.set_editor_property('options', options)
            task.set_editor_property('automated', True)
            task.set_editor_property('object', object)
            task.set_editor_property(
                'filename', f"{stagingdir}/{fbx_filename}")
            task.set_editor_property('prompt', False)
            task.set_editor_property('selected', False)

            unreal.Exporter.run_asset_export_task(task)

            transfers.append((
                f"{stagingdir}/{fbx_filename}", 
                f"{resources_dir}/{fbx_filename}"))

            json_element = {
                'material': str(name),
                'filename': fbx_filename
            }
            json_data.append(json_element)

        json_filename = f"{instance.name}.json"
        json_path = os.path.join(stagingdir, json_filename)

        with open(json_path, "w+") as file:
            json.dump(json_data, fp=file, indent=2)

        if "transfers" not in instance.data:
            instance.data["transfers"] = []
        if "representations" not in instance.data:
            instance.data["representations"] = []

        json_representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": stagingdir,
        }

        instance.data["representations"].append(json_representation)
        instance.data["transfers"].extend(transfers)
