# -*- coding: utf-8 -*-
"""Create look in Unreal."""
import unreal  # noqa
from openpype.hosts.unreal.api import pipeline, plugin


class CreateLook(plugin.Creator):
    """Shader connections defining shape look."""

    name = "unrealLook"
    label = "Unreal - Look"
    family = "look"
    icon = "paint-brush"

    root = "/Game/Avalon/Assets"
    suffix = "_INS"

    def __init__(self, *args, **kwargs):
        super(CreateLook, self).__init__(*args, **kwargs)

    def process(self):
        name = self.data["subset"]

        selection = []
        if (self.options or {}).get("useSelection"):
            sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
            selection = [a.get_path_name() for a in sel_objects]

        # Create the folder
        path = f"{self.root}/{self.data['asset']}"
        new_name = pipeline.create_folder(path, name)
        full_path = f"{path}/{new_name}"

        # Create a new cube static mesh
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        cube = ar.get_asset_by_object_path("/Engine/BasicShapes/Cube.Cube")

        # Create the avalon publish instance object
        container_name = f"{name}{self.suffix}"
        pipeline.create_publish_instance(
            instance=container_name, path=full_path)

        # Get the mesh of the selected object
        original_mesh = ar.get_asset_by_object_path(selection[0]).get_asset()
        materials = original_mesh.get_editor_property('materials')

        self.data["members"] = []

        # Add the materials to the cube
        for material in materials:
            name = material.get_editor_property('material_slot_name')
            object_path = f"{full_path}/{name}.{name}"
            unreal_object = unreal.EditorAssetLibrary.duplicate_loaded_asset(
                cube.get_asset(), object_path
            )

            # Remove the default material of the cube object
            unreal_object.get_editor_property('static_materials').pop()

            unreal_object.add_material(
                material.get_editor_property('material_interface'))

            self.data["members"].append(object_path)

            unreal.EditorAssetLibrary.save_asset(object_path)

        pipeline.imprint(f"{full_path}/{container_name}", self.data)
