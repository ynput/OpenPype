# -*- coding: utf-8 -*-
import unreal

from openpype.pipeline import CreatorError
from openpype.hosts.unreal.api.pipeline import (
    create_folder
)
from openpype.hosts.unreal.api.plugin import (
    UnrealAssetCreator
)
from openpype.lib import UILabelDef


class CreateLook(UnrealAssetCreator):
    """Shader connections defining shape look."""

    identifier = "io.ayon.creators.unreal.look"
    label = "Look"
    family = "look"
    icon = "paint-brush"

    def create(self, subset_name, instance_data, pre_create_data):
        # We need to set this to True for the parent class to work
        pre_create_data["use_selection"] = True
        sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
        selection = [a.get_path_name() for a in sel_objects]

        if len(selection) != 1:
            raise CreatorError("Please select only one asset.")

        selected_asset = selection[0]

        look_directory = "/Game/Ayon/Looks"

        # Create the folder
        folder_name = create_folder(look_directory, subset_name)
        path = f"{look_directory}/{folder_name}"

        instance_data["look"] = path

        # Create a new cube static mesh
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        cube = ar.get_asset_by_object_path("/Engine/BasicShapes/Cube.Cube")

        # Get the mesh of the selected object
        original_mesh = ar.get_asset_by_object_path(selected_asset).get_asset()
        materials = original_mesh.get_editor_property('static_materials')

        pre_create_data["members"] = []

        # Add the materials to the cube
        for material in materials:
            mat_name = material.get_editor_property('material_slot_name')
            object_path = f"{path}/{mat_name}.{mat_name}"
            unreal_object = unreal.EditorAssetLibrary.duplicate_loaded_asset(
                cube.get_asset(), object_path
            )

            # Remove the default material of the cube object
            unreal_object.get_editor_property('static_materials').pop()

            unreal_object.add_material(
                material.get_editor_property('material_interface'))

            pre_create_data["members"].append(object_path)

            unreal.EditorAssetLibrary.save_asset(object_path)

        super(CreateLook, self).create(
            subset_name,
            instance_data,
            pre_create_data)

    def get_pre_create_attr_defs(self):
        return [
            UILabelDef("Select the asset from which to create the look.")
        ]
