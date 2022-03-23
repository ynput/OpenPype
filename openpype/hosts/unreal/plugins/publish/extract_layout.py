# -*- coding: utf-8 -*-
import os
import json
import math

from bson.objectid import ObjectId

import unreal
from unreal import EditorLevelLibrary as ell
from unreal import EditorAssetLibrary as eal

import openpype.api
from avalon import io


class ExtractLayout(openpype.api.Extractor):
    """Extract a layout."""

    label = "Extract Layout"
    hosts = ["unreal"]
    families = ["layout"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        staging_dir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        # Check if the loaded level is the same of the instance
        current_level = ell.get_editor_world().get_path_name()
        assert current_level == instance.data.get("level"), \
            "Wrong level loaded"

        json_data = []

        for member in instance[:]:
            actor = ell.get_actor_reference(member)
            mesh = None

            # Check type the type of mesh
            if actor.get_class().get_name() == 'SkeletalMeshActor':
                mesh = actor.skeletal_mesh_component.skeletal_mesh
            elif actor.get_class().get_name() == 'StaticMeshActor':
                mesh = actor.static_mesh_component.static_mesh

            if mesh:
                # Search the reference to the Asset Container for the object
                path = unreal.Paths.get_path(mesh.get_path_name())
                filter = unreal.ARFilter(
                    class_names=["AssetContainer"], package_paths=[path])
                ar = unreal.AssetRegistryHelpers.get_asset_registry()
                try:
                    asset_container = ar.get_assets(filter)[0].get_asset()
                except IndexError:
                    self.log.error("AssetContainer not found.")
                    return

                parent = eal.get_metadata_tag(asset_container, "parent")
                family = eal.get_metadata_tag(asset_container, "family")

                self.log.info("Parent: {}".format(parent))
                blend = io.find_one(
                    {
                        "type": "representation",
                        "parent": ObjectId(parent),
                        "name": "blend"
                    },
                    projection={"_id": True})
                blend_id = blend["_id"]

                json_element = {}
                json_element["reference"] = str(blend_id)
                json_element["family"] = family
                json_element["instance_name"] = actor.get_name()
                json_element["asset_name"] = mesh.get_name()
                import_data = mesh.get_editor_property("asset_import_data")
                json_element["file_path"] = import_data.get_first_filename()
                transform = actor.get_actor_transform()

                json_element["transform"] = {
                    "translation": {
                        "x": -transform.translation.x,
                        "y": transform.translation.y,
                        "z": transform.translation.z
                    },
                    "rotation": {
                        "x": math.radians(transform.rotation.euler().x),
                        "y": math.radians(transform.rotation.euler().y),
                        "z": math.radians(180.0 - transform.rotation.euler().z)
                    },
                    "scale": {
                        "x": transform.scale3d.x,
                        "y": transform.scale3d.y,
                        "z": transform.scale3d.z
                    }
                }
                json_data.append(json_element)

        json_filename = "{}.json".format(instance.name)
        json_path = os.path.join(staging_dir, json_filename)

        with open(json_path, "w+") as file:
            json.dump(json_data, fp=file, indent=2)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        json_representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(json_representation)
