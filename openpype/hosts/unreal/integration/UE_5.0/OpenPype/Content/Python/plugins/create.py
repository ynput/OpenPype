import ast

import unreal

from pipeline import (
    create_publish_instance,
    imprint,
)


def new_publish_instance(
        instance_name, path, str_instance_data, str_members
):
    instance_data = ast.literal_eval(str_instance_data)
    members = ast.literal_eval(str_members)

    pub_instance = create_publish_instance(instance_name, path)

    pub_instance.set_editor_property('add_external_assets', True)
    assets = pub_instance.get_editor_property('asset_data_external')

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    for member in members:
        obj = ar.get_asset_by_object_path(member).get_asset()
        assets.add(obj)

    imprint(f"{path}/{instance_name}", instance_data)


def create_look(selected_asset, path):
    # Create a new cube static mesh
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    cube = ar.get_asset_by_object_path("/Engine/BasicShapes/Cube.Cube")

    # Get the mesh of the selected object
    original_mesh = ar.get_asset_by_object_path(selected_asset).get_asset()
    materials = original_mesh.get_editor_property('static_materials')

    members = []

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

        members.append(object_path)

        unreal.EditorAssetLibrary.save_asset(object_path)

    return members
