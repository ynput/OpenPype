import os

import bpy

import openpype.api
from openpype.hosts.blender.api import plugin


class ExtractBlend(openpype.api.Extractor):
    """Extract a blend file."""

    label = "Extract Blend"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout", "setdress"]
    optional = True

    @staticmethod
    def _pack_images_from_objects(objects):
        """Pack images from mesh objects materials."""
        # Get all objects materials using node tree shader.
        materials = set()
        for obj in objects:
            for mtl_slot in obj.material_slots:
                if (
                    mtl_slot.material and
                    mtl_slot.material.use_nodes and
                    mtl_slot.material.node_tree.type == 'SHADER'
                ):
                    materials.add(mtl_slot.material)
        # Get ShaderNodeTexImage from material node_tree.
        shader_texture_nodes = set()
        for material in materials:
            for node in material.node_tree.nodes:
                if (
                    isinstance(node, bpy.types.ShaderNodeTexImage) and
                    node.image
                ):
                    shader_texture_nodes.add(node)
        # Pack ShaderNodeTexImage images.
        for node in shader_texture_nodes:
            node.image.pack()

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        data_blocks = set()
        objects = set()

        for obj in instance:
            data_blocks.add(obj)
            # Get reference from override library.
            if obj.override_library and obj.override_library.reference:
                data_blocks.add(obj.override_library.reference)
            # Store objects to pack images from their materials.
            if isinstance(obj, bpy.types.Object):
                objects.add(obj)

        # Pack used images in the blend files.
        self._pack_images_from_objects(objects)

        bpy.ops.file.make_paths_absolute()
        bpy.data.libraries.write(filepath, data_blocks)

        plugin.deselect_all()

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'blend',
            'ext': 'blend',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s",
                      instance.name, representation)
