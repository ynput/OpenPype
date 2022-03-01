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
        Local_instances = list()
        for collection in bpy.data.collections:
            if collection.get("avalon"):
                avalon_dict = collection.get("avalon")
                if avalon_dict.get("id") == "pyblish.avalon.container":
                    if is_local_collection(collection):
                        Local_instances.append(collection)

        # bpy.ops.object.make_local(type='ALL')
        for collection in Local_instances:
            # Create a temp scene
            new_scene = bpy.data.scenes.new("temp_scene")

            # List of data blocks to extract
            data_blocks = set()

            # Get the name of the container in the publish file
            original_container_name = collection["avalon"][
                "original_container_name"
            ]

            name_space = collection["avalon"]["namespace"]

            # Link the collection to the temp scene
            new_scene.collection.children.link(collection)

            # Rename the object without the name space
            for object in collection.all_objects:
                current_object_name = object.name
                object.name = current_object_name.replace(
                    name_space + ":", ""
                )
                mesh = object.data
                current_mesh_name = mesh.name
                mesh.name = current_mesh_name.replace(name_space + ":", "")
                object.select_set(True)
                # mesh.select_set(True)


            # Rename the collection with his original name
            collection.name = original_container_name

            # Add collection to the data block to extract
            data_blocks.add(collection)


            scene.name = "scene_temp"

            new_scene.name = "Scene"

            # Add the scene to the data block to extract
            data_blocks.add(new_scene)

            # Get the parent  (work file ) of the instance
            metadata = collection.get(AVALON_PROPERTY)
            parent = metadata["parent"]
            representation = io.find_one({"_id": io.ObjectId(parent)})

            # Get the file path of the work file of the instance
            source = representation["data"]["source"]
            low_platform = platform.system().lower()
            root_work = instance.data["projectEntity"]["config"]["roots"][
                "work"
            ][low_platform]
            path = source.replace("{root[work]}", root_work)

            # Get the version_up of the path
            filepath = version_up(path)

            # Save the new work version
            #save_file(filepath, copy=False)
            bpy.data.libraries.write(filepath, data_blocks, fake_user=True)

            # Clean the scene
            bpy.data.scenes.remove(new_scene)
            scene.name = "Scene"
