import os

import bpy

import openpype.api


class ExtractBlendLook(openpype.api.Extractor):
    """Extract a blend file with materials and meshes."""

    label = "Extract Look"
    hosts = ["blender"]
    families = ["look"]
    optional = True

    pack_images = True

    @staticmethod
    def _get_images_from_materials(materials):
        """Get images from materials."""
        # Get ShaderNodeTexImage from material with node_tree.
        images = set()
        for material in materials:
            if (
                material.use_nodes
                and material.node_tree.type == "SHADER"
            ):
                for node in material.node_tree.nodes:
                    if (
                        isinstance(node, bpy.types.ShaderNodeTexImage)
                        and node.image
                    ):
                        images.add(node.image)
        return images

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.mat.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        data_blocks = set()
        objects = set()
        collection = instance[-1]

        for obj in instance:
            # Store objects to pack images from their materials.
            if isinstance(obj, bpy.types.Object) and obj.type == "MESH":
                objects.add(obj)
                data_blocks.add(obj)

        # Get all objects materials.
        materials = set()
        materials_assignment = dict()
        materials_indexes = dict()
        for obj in objects:
            if len(obj.material_slots):
                obj_materials = list()
                for mtl_slot in obj.material_slots:
                    material = mtl_slot.material
                    if material:
                        material.use_fake_user = True
                        materials.add(material)
                        data_blocks.add(material)
                    obj_materials.append(material)

                materials_assignment[obj.name] = obj_materials

                # Get polygons material indexes for objects.
                if len(obj_materials) > 1:
                    materials_indexes[obj.name] = [
                        face.material_index
                        for face in obj.data.polygons
                    ]

        # Get all images used by materials and pack their if needed.
        for image in self._get_images_from_materials(materials):
            if self.pack_images and not image.packed_file:
                image.pack()
            data_blocks.add(image)

        data_blocks.update({*bpy.data.textures, *bpy.data.node_groups})

        # Store materials assignment and indexes informations.
        collection["materials_assignment"] = materials_assignment
        collection["materials_indexes"] = materials_indexes

        data_blocks.add(collection)

        bpy.data.libraries.write(filepath, data_blocks, path_remap="ABSOLUTE")

        del collection["materials_assignment"]
        del collection["materials_indexes"]

        for material in materials:
            material.use_fake_user = False

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
