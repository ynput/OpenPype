# -*- coding: utf-8 -*-
import json
import os

import unreal
from unreal import MaterialEditingLibrary as mat_lib

import openpype.api


class ExtractLook(openpype.api.Extractor):
    """Extract look."""

    label = "Extract Look"
    hosts = ["unreal"]
    families = ["look"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        staging_dir = self.staging_dir(instance)
        resources_dir = instance.data["resourcesDir"]

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        transfers = []

        json_data = []

        for member in instance:
            asset = ar.get_asset_by_object_path(member)
            object = asset.get_asset()

            name = asset.get_editor_property('asset_name')

            json_element = {'material': str(name)}

            material_obj = object.get_editor_property('static_materials')[0]
            material = material_obj.material_interface

            base_color = mat_lib.get_material_property_input_node(
                material, unreal.MaterialProperty.MP_BASE_COLOR)

            base_color_name = base_color.get_editor_property('parameter_name')

            texture = mat_lib.get_material_default_texture_parameter_value(
                material, base_color_name)

            if texture:
                # Export Texture
                tga_filename = f"{instance.name}_{name}_texture.tga"

                tga_exporter = unreal.TextureExporterTGA()

                tga_export_task = unreal.AssetExportTask()

                tga_export_task.set_editor_property('exporter', tga_exporter)
                tga_export_task.set_editor_property('automated', True)
                tga_export_task.set_editor_property('object', texture)
                tga_export_task.set_editor_property(
                    'filename', f"{staging_dir}/{tga_filename}")
                tga_export_task.set_editor_property('prompt', False)
                tga_export_task.set_editor_property('selected', False)

                unreal.Exporter.run_asset_export_task(tga_export_task)

                json_element['tga_filename'] = tga_filename

                transfers.append((
                    f"{staging_dir}/{tga_filename}",
                    f"{resources_dir}/{tga_filename}"))

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
                'filename', f"{staging_dir}/{fbx_filename}")
            task.set_editor_property('prompt', False)
            task.set_editor_property('selected', False)

            unreal.Exporter.run_asset_export_task(task)

            json_element['fbx_filename'] = fbx_filename

            transfers.append((
                f"{staging_dir}/{fbx_filename}",
                f"{resources_dir}/{fbx_filename}"))

            json_data.append(json_element)

        json_filename = f"{instance.name}.json"
        json_path = os.path.join(staging_dir, json_filename)

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
            "stagingDir": staging_dir,
        }

        instance.data["representations"].append(json_representation)
        instance.data["transfers"].extend(transfers)
