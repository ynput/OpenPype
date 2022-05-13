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

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        data_blocks = set()

        for obj in instance:
            data_blocks.add(obj)
            # Get reference from override library.
            if obj.override_library and obj.override_library.reference:
                data_blocks.add(obj.override_library.reference)
            # Pack used images in the blend files.
            if isinstance(obj, bpy.types.Object) and obj.type == 'MESH':
                obj.select_set(True)
                for mtl_slot in obj.material_slots:
                    if (
                        mtl_slot.material and
                        mtl_slot.material.use_nodes and
                        mtl_slot.material.node_tree.type == 'SHADER'
                    ):
                        for node in mtl_slot.material.node_tree.nodes:
                            if (
                                node.bl_idname == 'ShaderNodeTexImage' and
                                node.image
                            ):
                                node.image.pack()

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
