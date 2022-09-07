import os

import bpy

import openpype.api


class ExtractBlendNodegroup(openpype.api.Extractor):
    """Extract a blend file with nodegroups."""

    label = "Extract Blender Nodegroup"
    hosts = ["blender"]
    families = ["blender.nodegroup"]
    optional = True

    pack_images = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.node.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        # Get all node groups and related objects
        node_groups = set()
        data_blocks = set()
        for obj in [
            o
            for o in instance
            if isinstance(o, bpy.types.Object) and o.type == "MESH"
        ]:
            if hasattr(obj, "modifiers"):
                data_blocks.add(obj)
                for mod in [m for m in obj.modifiers if m.type == "NODES"]:
                    group = mod.node_group
                    if group:
                        group.use_fake_user = True
                        node_groups.add(group)

        # Add node groups to data
        data_blocks.update(node_groups)

        # Add collection to library
        data_blocks.add(instance[-1])

        # Write datablock into file
        bpy.data.libraries.write(filepath, data_blocks, path_remap="ABSOLUTE")

        # Restore fake user
        for group in node_groups:
            group.use_fake_user = False

        # Register representation
        instance.data.setdefault("representations", [])

        representation = {
            "name": "blend",
            "ext": "blend",
            "files": filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: {representation}"
        )
