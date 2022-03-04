import os

import bpy
from avalon import io

import openpype.api


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
        self.log.info(dir(self))
        self.log.info(self.hosts)

        # Create data block set
        data_blocks = set()

        # Get instance collection
        collection = bpy.data.collections[instance.name]
        data_blocks.add(collection)
        for obj in collection.objects:
            data_blocks.add(obj)
            # Pack used images in the blend files.
            if obj.type == "MESH":
                for material_slot in obj.material_slots:
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
