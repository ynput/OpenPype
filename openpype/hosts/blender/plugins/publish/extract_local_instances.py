import os
import bpy
import platform

from avalon import io
import openpype.api
from openpype.lib import version_up
from openpype.hosts.blender.api.workio import save_file
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.api.plugin import is_local_collection


class ExtractLocalInstances(openpype.api.Extractor):
    """Extract local instance as a blend file."""

    label = "Extract local instance"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout"]
    optional = True

    def process(self, instance):
        # Define extract output file path

        # Get the main scene
        scene = bpy.data.scenes["Scene"]

        # Get the local instances
        local_instances_list = list()
        for collection in bpy.data.collections:
            if collection.override_library is not None:
                if collection.get("avalon"):
                    avalon_dict = collection.get("avalon")
                    if avalon_dict.get("id") == "pyblish.avalon.container":
                        if is_local_collection(collection):
                            local_instances_list.append(collection)

        self.log.info(
            "Container: %s\nRepresentation: %s", collection.name, local_instances_list
        )
        # bpy.ops.object.make_local(type='ALL')
        for collection in local_instances_list:

            # Create a temp scene
            new_scene = bpy.data.scenes.new("temp_scene")

            # List of data blocks to extract
            data_blocks = set()

            # Get library override
            library_override_collection = collection.override_library.reference
            library_override_collection_copy = library_override_collection.copy()
            # Link the collection to the temp scene
            new_scene.collection.children.link(library_override_collection_copy)

            # Rename the collection with his original name

            # Add collection to the data block to extract
            data_blocks.add(library_override_collection_copy)

            scene.name = "scene_temp"

            new_scene.name = "Scene"

            # Add the scene to the data block to extract
            data_blocks.add(new_scene)

            # Get the parent  (work file ) of the instance
            metadata = collection.get(AVALON_PROPERTY)
            parent = metadata["parent"]
            representation = io.find_one({"_id": io.ObjectId(parent)})
            self.log.info("Container: %s\nRepresentation: %s", "metadata", metadata)
            # Get the file path of the work file of the instance
            self.log.info(
                "Container: %s\nRepresentation: %s",
                "representation",
                representation,
            )
            source = representation["data"]["source"]
            low_platform = platform.system().lower()
            root_work = instance.data["projectEntity"]["config"]["roots"]["work"][
                low_platform
            ]
            path = source.replace("{root[work]}", root_work)

            self.log.info(path)
            # Get the version_up of the path
            filepath = version_up(path)
            self.log.info(filepath)
            # Save the new work version
            # save_file(filepath, copy=False)

            # bpy.data.libraries.write(filepath, data_blocks, fake_user=True)

            # Clean the scene
        #  bpy.data.scenes.remove(new_scene)
        #    scene.name = "Scene"
