import os

import bpy
from bson.objectid import ObjectId

import openpype.api
from openpype.pipeline import AVALON_CONTAINER_ID
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    metadata_update,
    AVALON_PROPERTY,
)


class ExtractSceneRender(openpype.api.Extractor):
    """Extract the scene as blend file."""

    label = "Extract Scene Render"
    hosts = ["blender"]
    families = ["render"]
    optional = True

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        data_blocks = set()

        # Adding all members of the instance to data blocks that will be
        # written into the blender library.
        for member in instance:
            data_blocks.add(member)
            # Get reference from override library.
            if member.override_library and member.override_library.reference:
                data_blocks.add(member.override_library.reference)

        # Store instance metadata
        instance_collection = instance[-1]
        instance_metadata = instance_collection[AVALON_PROPERTY].to_dict()
        instance_collection[AVALON_PROPERTY] = dict()

        # Adding all scenes who contain the instance_collection
        for scene in bpy.data.scenes:
            childrens = plugin.get_children_recursive(scene.collection)
            if instance_collection in childrens:
                data_blocks.add(scene)

        # Create ID to allow blender import without using OP tools
        repre_id = str(ObjectId())

        # Add container metadata to collection
        metadata_update(
            instance_collection,
            {
                "schema": "openpype:container-2.0",
                "id": AVALON_CONTAINER_ID,
                "name": instance_metadata["subset"],
                "representation": repre_id,
                "asset_name": instance_metadata["asset"],
                "parent": str(instance.data["assetEntity"]["parent"]),
                "family": instance.data["family"],
            },
        )

        bpy.ops.file.make_paths_absolute()
        bpy.data.libraries.write(filepath, data_blocks)

        # restor instance metadata
        instance_collection[AVALON_PROPERTY] = instance_metadata

        plugin.deselect_all()

        # Create representation dict
        representation = {
            "name": "blend",
            "ext": "blend",
            "files": filename,
            "stagingDir": stagingdir,
            "id": repre_id,
        }
        instance.data.setdefault("representations", [])
        instance.data["representations"].append(representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: {representation}"
        )
