import os

import bpy

from openpype.pipeline import publish


class ExtractBlend(publish.Extractor, publish.OptionalPyblishPluginMixin):
    """Extract a blend file."""

    label = "Extract Blend"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout", "blendScene"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        asset_name = instance.data["assetEntity"]["name"]
        subset = instance.data["subset"]
        instance_name = f"{asset_name}_{subset}"
        filename = f"{instance_name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.debug("Performing extraction..")

        data_blocks = set()

        for data in instance:
            data_blocks.add(data)
            # Pack used images in the blend files.
            if not (
                isinstance(data, bpy.types.Object) and data.type == 'MESH'
            ):
                continue
            for material_slot in data.material_slots:
                mat = material_slot.material
                if not (mat and mat.use_nodes):
                    continue
                tree = mat.node_tree
                if tree.type != 'SHADER':
                    continue
                for node in tree.nodes:
                    if node.bl_idname != 'ShaderNodeTexImage':
                        continue
                    # Check if image is not packed already
                    # and pack it if not.
                    if node.image and node.image.packed_file is None:
                        node.image.pack()

        bpy.data.libraries.write(filepath, data_blocks)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'blend',
            'ext': 'blend',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.debug("Extracted instance '%s' to: %s",
                       instance.name, representation)
