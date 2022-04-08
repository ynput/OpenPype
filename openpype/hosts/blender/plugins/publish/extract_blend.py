import os

import bpy
from avalon import io, api

import openpype.api
from openpype.hosts.blender.api import plugin


class ExtractBlend(openpype.api.Extractor):
    """Extract a blend file."""

    label = "Extract Blend"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")
        plugin.remove_orphan_datablocks()
        plugin.remove_orphan_datablocks()
        # Create data block set
        data_blocks = set()

        # Get instance collection
        container = bpy.data.collections[instance.name]
        objects = plugin.get_all_objects_in_collection(container)
        collections = plugin.get_all_collections_in_collection(container)

        plugin.remove_orphan_datablocks()

        plugin.remove_namespace_for_objects_container(container)

        has_namespace = api.Session["AVALON_TASK"] in [
            "Rigging",
            "Modeling",
        ]
        for collection in collections:
            # remove the namespace if exists
            if not collection.get("original_name"):
                collection["original_name"] = collection.name
                collection.property_overridable_library_set(
                    '["original_name"]', True
                )

                if has_namespace:
                    collection["namespace"] = container.name
                    collection.property_overridable_library_set(
                        '["namespace"]', True
                    )

        data_blocks.add(container)
        for object in objects:
            data_blocks.add(object)

            # if doesn't exist create the custom property original_name
            if not object.get("original_name"):

                object["original_name"] = object.name
                object.property_overridable_library_set(
                    '["original_name"]', True
                )
                if object.type != "EMPTY":
                    object.data["original_name"] = object.data.name
                    object.data.property_overridable_library_set(
                        '["original_name"]', True
                    )

            if has_namespace:

                object["namespace"] = container.name
                object.property_overridable_library_set('["namespace"]', True)
                if object.type != "EMPTY":
                    object.data["namespace"] = container.name
                    object.data.property_overridable_library_set(
                        '["namespace"]', True
                    )

            # Pack used images in the blend files.
            if object.type == "MESH":
                for material_slot in object.material_slots:
                    mat = material_slot.material
                    if mat and mat.use_nodes:
                        tree = mat.node_tree
                        if tree.type == "SHADER":
                            for node in tree.nodes:
                                if node.bl_idname == "ShaderNodeTexImage":
                                    if node.image:
                                        node.image.pack()

        # Create and set representation to the instance data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "blend",
            "ext": "blend",
            "files": filename,
            "stagingDir": stagingdir,
        }

        instance.data["representations"].append(representation)
        # Write the .blend library with data_blocks collected
        bpy.data.libraries.write(filepath, data_blocks)
